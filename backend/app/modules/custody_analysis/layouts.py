"""Layout parsers: read the custody report workbooks into canonical facts without changing any source value.

Principles
* One fact per non-zero amount, with its source cell/row reference. Blank cells are not facts (never zero-filled);
  explicit zeros are kept out of the facts but recorded as "presence" so a branch that reported nothing is visible.
* Dimensions the file does not carry stay NULL (e.g. the year, a branch) — the report then states the limitation.
* Whatever disagrees with the file's own totals, or looks wrong, becomes an issue; nothing is corrected.
"""
import io
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from openpyxl import load_workbook

from app.core.cleaning.normalizers import normalize_text

MONTHS = {  # normalised (hamza/ya folded) names -> month number
    "يناير": 1, "jan": 1, "january": 1, "فبراير": 2, "feb": 2, "february": 2, "مارس": 3, "mar": 3, "march": 3,
    "ابريل": 4, "ابرايل": 4, "apr": 4, "april": 4, "مايو": 5, "may": 5, "يونيو": 6, "يونيه": 6, "jun": 6, "june": 6,
    "يوليو": 7, "يوليه": 7, "jul": 7, "july": 7, "اغسطس": 8, "aug": 8, "august": 8, "سبتمبر": 9, "sep": 9,
    "sept": 9, "september": 9, "اكتوبر": 10, "oct": 10, "october": 10, "نوفمبر": 11, "nov": 11, "november": 11,
    "ديسمبر": 12, "dec": 12, "december": 12,
}
TOTAL_WORDS = {"total", "grand total", "الاجمالي", "اجمالي", "الاجمالي الفرعي", "الاجمالي الكلي"}
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_GROUP = re.compile(r"^\s*(فروع|branches)\b", re.I)
_HEAD_OFFICE = {"head office", "المركز الرئيسي", "المركز الرئيسى", "مركز رئيسي"}


class UnrecognisedLayout(ValueError):
    pass


@dataclass
class FactRow:
    source_ref: str
    month: int | None
    amount: Decimal
    year: int | None = None
    scope: str = "unspecified"
    branch_label: str | None = None
    branch_kind: str | None = None
    cost_center: str | None = None
    category: str | None = None
    item: str | None = None
    account_no: str | None = None
    holder: str | None = None
    ref_no: str | None = None
    description: str | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class Issue:
    code: str
    severity: str  # info | warning | critical
    message: str
    count: int = 1
    examples: list[str] = field(default_factory=list)


@dataclass
class ControlTotal:
    label: str
    month: int | None
    stated: Decimal | None
    computed: Decimal
    source_ref: str
    note: str = ""


@dataclass
class Parsed:
    layout: str
    scope_label: str
    title: str | None = None
    year: int | None = None
    year_source: str = "none"
    facts: list[FactRow] = field(default_factory=list)
    presence: list[dict] = field(default_factory=list)  # {month, label, kind, total, source_ref}
    issues: list[Issue] = field(default_factory=list)
    controls: list[ControlTotal] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)  # category as written -> Arabic/other label given by the file
    sheets: list[str] = field(default_factory=list)
    skipped_sheets: list[str] = field(default_factory=list)

    def issue(self, code: str, severity: str, message: str, example: str | None = None):
        for i in self.issues:
            if i.code == code:
                i.count += 1
                if example and len(i.examples) < 8:
                    i.examples.append(example)
                return
        self.issues.append(Issue(code, severity, message, 1, [example] if example else []))


# ---------------------------------------------------------------------------- helpers
def _dec(v) -> Decimal | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float, Decimal)):
        d = Decimal(repr(float(v))) if isinstance(v, float) else Decimal(v)
        return d.quantize(Decimal("0.0001"))
    return None


def _txt(v) -> str:
    return " ".join(str(v).split()) if v is not None else ""


def month_of(text) -> int | None:
    n = normalize_text(text)
    for tok in n.split():
        if tok in MONTHS:
            return MONTHS[tok]
    return None


def year_of(text) -> int | None:
    m = _YEAR.search(str(text or ""))
    return int(m.group(1)) if m else None


def _used_rows(ws) -> list[int]:
    """Rows that really hold a value (some sheets claim a million rows because of a stray formatted cell)."""
    return sorted({r for (r, _c), cell in ws._cells.items() if cell.value is not None})


def _row(ws, r: int, upto: int = 45) -> dict[int, object]:
    return {c: ws.cell(r, c).value for c in range(1, upto + 1) if ws.cell(r, c).value is not None}


def _is_total_label(v) -> bool:
    n = normalize_text(v)
    return n in TOTAL_WORDS or n.startswith("الاجمالي")


def _branch_kind(label: str) -> str:
    n = normalize_text(label)
    if label.strip().lower() in _HEAD_OFFICE or n in _HEAD_OFFICE or n == "head office":
        return "head_office"
    return "group" if _GROUP.match(label) else "branch"


def _scope_of(kind: str) -> str:
    return "head_office" if kind == "head_office" else "branch"


def sheet_kind(ws) -> str:
    r1 = {c: normalize_text(v) for c, v in _row(ws, 1, 12).items()}
    vals = set(r1.values())
    if {"amount", "branch"} <= vals and "class 1" in vals:
        return "gl"
    if "البيان" in vals and any("تاريخ الصرف" in v for v in vals):
        return "branch_wide"
    if any("مبلغ السلفه" in v for v in vals):
        return "advances"
    a1 = r1.get(1, "")
    if a1 == "branch":
        return "branch_pivot"
    if a1 == "acc name":
        return "custodian_cols_pivot"
    if a1 in ("row labels", "employees"):
        return "row_pivot"
    if normalize_text(ws.title) == "total" or (a1 == "الشهر" and r1.get(2) == "total"):
        return "totals"
    return "unknown"


def detect_layout(content: bytes) -> str | None:
    """Layout name by sheet kinds (None when unknown: parse_workbook then reports it)."""
    wb = load_workbook(io.BytesIO(content), data_only=True)
    present = {sheet_kind(ws) for ws in wb}
    if "gl" in present:
        return "gl_settlement_lines"
    return "advance_register" if "advances" in present else None


# ---------------------------------------------------------------------------- entry point
def parse_workbook(content: bytes, filename: str = "", year: int | None = None, layout: str | None = None,
                   scope_hint: str | None = None) -> Parsed:
    wb = load_workbook(io.BytesIO(content), data_only=True)
    kinds = {ws.title: sheet_kind(ws) for ws in wb}
    present = set(kinds.values())
    if layout is None:
        if "gl" in present:
            layout = "gl_settlement_lines"
        elif "advances" in present:
            layout = "advance_register"
        elif present & {"branch_wide", "branch_pivot"} and not present & {"custodian_cols_pivot"}:
            layout = "monthly_branch_expense"
        elif present & {"custodian_cols_pivot"} or ("row_pivot" in present):
            layout = "monthly_custodian_expense"
        else:
            raise UnrecognisedLayout("This workbook does not match a known custody report layout "
                                     f"(sheet kinds: {sorted(present)})")
    if layout == "advance_register":
        raise UnrecognisedLayout("Advance registers are read by advances.parse_advances (handled by the service)")
    if layout == "gl_settlement_lines":
        return _parse_gl(wb, kinds, year)
    if layout == "monthly_branch_expense":
        return _parse_monthly(wb, kinds, year, "monthly_branch_expense", "branches", "branch")
    if layout == "monthly_custodian_expense":
        return _parse_monthly(wb, kinds, year, "monthly_custodian_expense", "head_office", scope_hint or "head_office")
    raise UnrecognisedLayout(f"Unknown layout '{layout}'")


# ---------------------------------------------------------------------------- F3: settlement journal (GL lines)
def _find_year(wb, skip: str) -> int | None:
    for ws in wb:
        if ws.title == skip:
            continue
        for r in _used_rows(ws)[:4]:
            for v in _row(ws, r, 12).values():
                y = year_of(v) if isinstance(v, str) else None
                if y:
                    return y
    return None


def _holder_from(desc: str) -> str | None:
    m = re.search(r"طرف\s+(.+)", desc)
    if not m:
        return None
    rest = m.group(1)
    stop = re.search(r"\s+(?:لسداد|للصرف|لشراء|لتدريب|لتركيب|لتغطية|تغطية|نظير|ل\S+)", rest)
    name = rest[:stop.start()] if stop else rest
    name = " ".join(name.split())
    return name or None


def _parse_gl(wb, kinds: dict, year_param: int | None) -> Parsed:
    main = next(t for t, k in kinds.items() if k == "gl")
    ws = wb[main]
    p = Parsed("gl_settlement_lines", "temporary_custody", sheets=[main])
    hdr = {normalize_text(v): c for c, v in _row(ws, 1, 12).items()}
    col = lambda *names: next((hdr[n] for n in names if n in hdr), None)  # noqa: E731
    c_amt, c_acc, c_cat, c_cc = col("amount"), col("acc name"), col("class 1"), col("class 2")
    c_br, c_desc, c_no, c_mon = col("branch"), col("deccription", "description"), col("number"), col("month")
    # period year: uploader > stated in the file (title of another sheet) > unknown
    year, ysrc = (year_param, "uploader") if year_param else (None, "none")
    if year is None:
        y = _find_year(wb, main)
        year, ysrc = (y, "file") if y else (None, "none")
    p.year, p.year_source = year, ysrc
    for t, k in kinds.items():
        if t != main:
            p.skipped_sheets.append(t)
            ws2 = wb[t]
            for r in _used_rows(ws2)[:2]:
                for v in _row(ws2, r, 3).values():
                    if isinstance(v, str) and ("Custod" in v or "عهد" in v) and not p.title:
                        p.title = _txt(v)
    cc_names: dict[str, Counter] = defaultdict(Counter)
    name_ccs: dict[str, set] = defaultdict(set)
    je_months: dict[str, set] = defaultdict(set)
    for r in _used_rows(ws):
        if r == 1:
            continue
        amt = _dec(ws.cell(r, c_amt).value)
        if amt is None:
            continue
        ref = f"{main}!R{r}"
        m = ws.cell(r, c_mon).value if c_mon else None
        month = int(m) if isinstance(m, (int, float)) and 1 <= int(m) <= 12 else None
        branch = _txt(ws.cell(r, c_br).value) or None
        kind = _branch_kind(branch) if branch else None
        cc = ws.cell(r, c_cc).value if c_cc else None
        cc = str(int(cc)) if isinstance(cc, (int, float)) else (_txt(cc) or None)
        desc = _txt(ws.cell(r, c_desc).value) if c_desc else None
        f = FactRow(ref, month, amt, year, _scope_of(kind) if kind else "unspecified", branch, kind, cc,
                    _txt(ws.cell(r, c_cat).value) or None, None,
                    str(ws.cell(r, c_acc).value) if c_acc and ws.cell(r, c_acc).value is not None else None,
                    _holder_from(desc) if desc else None, _txt(ws.cell(r, c_no).value) or None, desc)
        if month is None:
            f.flags.append("month_missing"); p.issue("month_missing", "warning", "Line without a valid month", ref)
        if amt < 0:
            f.flags.append("negative_amount"); p.issue("negative_amount", "warning", "Negative amount (kept as written)", ref)
        if f.ref_no and f.ref_no.upper() == "GL" or (desc and desc.lower().startswith("reclas")):
            f.flags.append("reclass_entry"); p.issue("reclass_entry", "info", "Manual reclassification entry (kept as written)", ref)
        if cc is None:
            f.flags.append("cost_center_missing"); p.issue("cost_center_missing", "warning", "Line without a cost-centre code", ref)
        elif branch:
            cc_names[cc][normalize_text(branch)] += 1
            name_ccs[normalize_text(branch)].add(cc)
        if desc and not f.holder and not f.flags.count("reclass_entry"):
            p.issue("holder_not_parsed", "info", "Custodian name could not be read from the description", ref)
        if f.ref_no and month:
            je_months[f.ref_no].add(month)
        p.facts.append(f)
    for cc, names in cc_names.items():
        if len(names) > 1:
            p.issue("cost_center_name_variants", "warning",
                    "One cost-centre code appears with different branch spellings", f"{cc}: " + " / ".join(sorted(names)))
    for nm, ccs in name_ccs.items():
        if len(ccs) > 1:
            p.issue("branch_multiple_cost_centers", "warning",
                    "One branch name appears under more than one cost-centre code", f"{nm}: " + ", ".join(sorted(ccs)))
    reused = [k for k, v in je_months.items() if len(v) > 1]
    if reused:
        p.issues.append(Issue("je_number_reused_across_months", "info",
                              "Journal-entry numbers restart every month (same number in several months); "
                              "lines are identified by month + number", len(reused), sorted(reused)[:8]))
    # controls: the file's own pivots (Sheet2/Sheet3) and Arabic labels
    _gl_controls(wb, kinds, main, p)
    return p


def _gl_controls(wb, kinds, main, p: Parsed) -> None:
    per_month: dict[int, Decimal] = defaultdict(Decimal)
    for f in p.facts:
        if f.month:
            per_month[f.month] += f.amount
    done = False
    for t in kinds:
        if t == main:
            continue
        ws = wb[t]
        rows = _used_rows(ws)
        hdr = total = None
        for r in rows:
            vals = _row(ws, r, 14)
            months = {c: int(v) for c, v in vals.items() if isinstance(v, (int, float)) and float(v).is_integer() and 1 <= int(v) <= 12}
            if hdr is None and len(months) >= 2 and len(months) == sum(1 for v in vals.values() if isinstance(v, (int, float))):
                hdr = (r, months)
            labels = [normalize_text(vals.get(1)), normalize_text(vals.get(2))]
            if hdr and r > hdr[0] and any(x in ("grand total", "total") for x in labels):
                total = r
            # Arabic expense label next to the English class (Sheet3): source-provided display names
            if vals.get(1) and vals.get(2) and isinstance(vals.get(1), str) and isinstance(vals.get(2), str) \
                    and normalize_text(vals.get(1)) not in ("نوع المصروف", "row labels"):
                if any("؀" <= ch <= "ۿ" for ch in vals[1]) and not any("؀" <= ch <= "ۿ" for ch in vals[2]):
                    p.labels[_txt(vals[2])] = _txt(vals[1])
        if hdr and total and not done:
            done = True
            for c, mnum in hdr[1].items():
                stated = _dec(ws.cell(total, c).value)
                p.controls.append(ControlTotal("Totals stated in the file's own pivot", mnum, stated,
                                               per_month.get(mnum, Decimal("0")), f"{t}!R{total}C{c}"))
            tc = max(c for c in _row(ws, total, 14) if c > max(hdr[1]))if any(c > max(hdr[1]) for c in _row(ws, total, 14)) else None
            if tc:
                p.controls.append(ControlTotal("Grand total stated in the file's own pivot", None, _dec(ws.cell(total, tc).value),
                                               sum(per_month.values(), Decimal("0")), f"{t}!R{total}C{tc}"))
    p.facts.sort(key=lambda f: (f.month or 0, f.source_ref))


# ---------------------------------------------------------------------------- F1/F2: monthly reports
def _parse_monthly(wb, kinds, year_param, layout, scope_label, default_scope) -> Parsed:
    p = Parsed(layout, scope_label)
    p.year, p.year_source = (year_param, "uploader") if year_param else (None, "none")
    totals_sheets = []
    for ws in wb:
        k = kinds[ws.title]
        if k == "totals":
            totals_sheets.append(ws)
            continue
        if k not in ("branch_wide", "branch_pivot", "custodian_cols_pivot", "row_pivot"):
            p.skipped_sheets.append(ws.title)
            continue
        p.sheets.append(ws.title)
        if k == "branch_wide":
            _branch_wide(ws, p)
        else:
            _pivot(ws, p, k, default_scope)
    if p.year is None:
        years = Counter(f.year for f in p.facts if f.year)
        if years:
            p.year, p.year_source = years.most_common(1)[0][0], "file"
    if p.year and any(f.year is None for f in p.facts):
        for f in p.facts:
            if f.year is None:
                f.year = p.year
                if "year_from_other_sheets" not in f.flags and p.year_source == "file":
                    f.flags.append("year_from_other_sheets")
        if p.year_source == "file":
            p.issue("year_from_other_sheets", "info", "Some sheets do not state the year; it was taken from the sheets that do", None)
    for pr in p.presence:
        pr.setdefault("year", p.year)
    _monthly_controls(p, totals_sheets)
    p.facts.sort(key=lambda f: (f.month or 0, f.source_ref))
    return p


def _title_month(ws) -> int | None:
    return month_of(ws.title)


def _branch_wide(ws, p: Parsed) -> None:
    rows = _used_rows(ws)
    hdr1, hdr2 = _row(ws, 1, 45), _row(ws, 2, 45)
    merged = {}
    for rng in ws.merged_cells.ranges:
        if rng.min_row == 1:
            for c in range(rng.min_col, rng.max_col + 1):
                merged[c] = _txt(ws.cell(1, rng.min_col).value)
    total_col = next((c for c, v in hdr1.items() if normalize_text(v).startswith("الاجمالي")), None)
    if total_col is None:
        p.issue("layout_unreadable", "critical", f"Sheet '{ws.title}': total column not found", ws.title)
        return
    cats: dict[int, tuple[str | None, str | None]] = {}
    for c in range(4, total_col):
        grp = _txt(hdr1.get(c)) or merged.get(c) or None
        item = _txt(hdr2.get(c)) or None
        if grp or item:
            cats[c] = (grp or item, item if grp else None)
    sheet_month = _title_month(ws)
    month = sheet_month
    subtotal_row = None
    after = []
    for r in rows:
        if r <= 2:
            continue
        a, b = ws.cell(r, 1).value, ws.cell(r, 2).value
        if _is_total_label(a) or _is_total_label(b):
            subtotal_row = r
            continue
        label = _txt(b)
        numeric = {c: _dec(ws.cell(r, c).value) for c in range(4, total_col + 1) if _dec(ws.cell(r, c).value) is not None}
        if subtotal_row is not None:
            if numeric:
                after.append(r)
            continue
        if not label:
            continue
        dt = ws.cell(r, 3).value
        if isinstance(dt, str):
            mm, yy = month_of(dt), year_of(dt)
            if mm and sheet_month and mm != sheet_month:
                p.issue("month_label_differs_from_sheet", "warning", "Row month label differs from the sheet's month", f"{ws.title}!R{r}")
            month = mm or sheet_month
            if yy and p.year is None:
                p.year, p.year_source = yy, "file"
        kind = _branch_kind(label)
        comp = Decimal("0")
        for c, (grp, item) in cats.items():
            v = numeric.get(c)
            if v is None or v == 0:
                continue
            comp += v
            p.facts.append(FactRow(f"{ws.title}!{ws.cell(r, c).coordinate}", month, v, None, _scope_of(kind), label, kind,
                                   None, grp, item))
        stated = numeric.get(total_col)
        flags = []
        if stated is None:
            if comp != 0:
                flags.append("row_total_missing")
                p.issue("row_total_missing", "warning", "Row without its own total cell (computed from components)", f"{ws.title}!R{r}")
        elif abs(stated - comp) > Decimal("0.5"):
            flags.append("row_total_differs_from_components")
            p.issue("row_total_differs_from_components", "warning",
                    "Row total stated in the file differs from the sum of its components (components are used)",
                    f"{ws.title}!R{r} {label}: stated {stated:.2f} vs components {comp:.2f}")
        if not isinstance(a := ws.cell(r, 1).value, (int, float)):
            p.issue("row_without_sequence_number", "info", "Branch row without a sequence number", f"{ws.title}!R{r}")
        p.presence.append({"month": month, "label": label, "kind": kind, "total": str(comp), "source_ref": f"{ws.title}!R{r}",
                           "flags": flags})
        for f in p.facts[-len(cats):]:
            if f.source_ref.startswith(f"{ws.title}!") and f.branch_label == label and flags and "row_" in flags[0]:
                f.flags.extend(x for x in flags if x not in f.flags)
    for (r, c), cell in ws._cells.items():
        if c > total_col and cell.value is not None and isinstance(cell.value, (int, float)) and cell.value != 0 \
                and (subtotal_row is None or r < subtotal_row):
            p.issue("stray_cells_outside_table", "info", "Helper cells outside the report table (ignored)", f"{ws.title}!{cell.coordinate}")
    if after:
        p.issue("rows_after_subtotal", "warning", "Rows below the sheet's subtotal row (not part of its stated total)",
                f"{ws.title}!R{after[0]}..R{after[-1]}")
    # control: subtotal row vs computed
    if subtotal_row is not None:
        stated = _dec(ws.cell(subtotal_row, total_col).value)
        computed = sum((f.amount for f in p.facts if f.source_ref.startswith(f"{ws.title}!")), Decimal("0"))
        p.controls.append(ControlTotal(f"Sheet subtotal ({ws.title.strip()})", month, stated, computed,
                                       f"{ws.title}!R{subtotal_row}"))
    else:
        p.issue("subtotal_row_missing", "info", "Sheet has no subtotal row", ws.title)


def _pivot(ws, p: Parsed, kind: str, default_scope: str) -> None:
    rows = _used_rows(ws)
    hdr = _row(ws, 1, 60)
    month = _title_month(ws)
    cols: list[tuple[int, str]] = []
    total_col = None
    for c in sorted(hdr):
        if c == 1:
            continue
        h = hdr[c]
        if isinstance(h, str) and (_is_total_label(h) or normalize_text(h).startswith("total")):
            total_col = c
            break
        if isinstance(h, str) and "نسبه" in normalize_text(h):
            break
        cols.append((c, _txt(h)))
    if not cols:
        p.issue("layout_unreadable", "critical", f"Sheet '{ws.title}': no category columns found", ws.title)
        return
    transposed = kind == "custodian_cols_pivot"
    if kind == "branch_pivot":
        scope_kind = "branch"
    elif kind == "custodian_cols_pivot":
        scope_kind = "head_office"
    else:
        scope_kind = default_scope if default_scope in ("head_office", "branch") else "unspecified"
        if "المركز" in ws.title:
            scope_kind = "head_office"
        if scope_kind == "unspecified":
            p.issue("scope_unknown", "warning", "Sheet scope (Head Office / branches) is not stated", ws.title)
    if month is None:
        p.issue("month_unknown", "critical", f"Sheet '{ws.title}': month could not be read from the sheet name", ws.title)
    total_row = None
    sheet_sum = Decimal("0")
    for r in rows:
        if r == 1:
            continue
        a = ws.cell(r, 1).value
        if _is_total_label(a):
            total_row = r
            continue
        label = _txt(a)
        if not label:
            continue
        comp = Decimal("0")
        for c, h in cols:
            v = _dec(ws.cell(r, c).value)
            if v is None or v == 0:
                continue
            comp += v
            ref = f"{ws.title}!{ws.cell(r, c).coordinate}"
            if transposed:
                p.facts.append(FactRow(ref, month, v, None, "head_office", None, "head_office", None, label, None, holder=h))
            elif scope_kind == "branch":
                bk = _branch_kind(label)
                p.facts.append(FactRow(ref, month, v, None, _scope_of(bk), label, bk, None, h, None))
            else:
                p.facts.append(FactRow(ref, month, v, None, scope_kind, None, "head_office" if scope_kind == "head_office" else None,
                                       None, h, None, holder=label))
        sheet_sum += comp
        stated = _dec(ws.cell(r, total_col).value) if total_col else None
        if stated is not None and abs(stated - comp) > Decimal("0.5"):
            p.issue("row_total_differs_from_components", "warning",
                    "Row total stated in the file differs from the sum of its components (components are used)",
                    f"{ws.title}!R{r}: stated {stated:.2f} vs components {comp:.2f}")
        if not transposed:
            p.presence.append({"month": month, "label": label,
                               "kind": _branch_kind(label) if scope_kind == "branch" else scope_kind,
                               "total": str(comp), "source_ref": f"{ws.title}!R{r}"})
    if total_row and total_col:
        stated = _dec(ws.cell(total_row, total_col).value)
        p.controls.append(ControlTotal(f"Sheet total ({ws.title.strip()})", month, stated, sheet_sum, f"{ws.title}!R{total_row}"))
    elif not total_row:
        p.issue("total_row_missing", "info", "Sheet has no total row", ws.title)


def _monthly_controls(p: Parsed, totals_sheets) -> None:
    """The workbook's own month totals (its `Total` sheet) against what the sheets add up to."""
    per_month: dict[int, Decimal] = defaultdict(Decimal)
    for f in p.facts:
        if f.month:
            per_month[f.month] += f.amount
    for ws in totals_sheets:
        for r in _used_rows(ws):
            m = month_of(ws.cell(r, 1).value)
            stated = _dec(ws.cell(r, 2).value)
            if m and stated is not None:
                p.controls.append(ControlTotal("Month total stated in the workbook's Total sheet", m, stated,
                                               per_month.get(m, Decimal("0")), f"{ws.title}!R{r}"))
