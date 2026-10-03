"""Asset register (fixed-asset export, e.g. an Oracle FA report): reader, observations and profile.

The register is stored AS RECEIVED, as reference master data. Nothing is edited or guessed: a cell that is empty stays NULL, a date that
the source wrote as text is kept as text (and parsed only where the format is unambiguous), a «life» written as text is not converted.
Observations (duplicates, inconsistent cells, dates beyond the report period) are reported, never fixed."""
import io
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from openpyxl import load_workbook

ZERO = Decimal(0)
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
# source header -> field
HEADERS = {
    "asset book": "asset_book", "asset number": "asset_number", "description": "description", "tag number": "tag_number", "serial number": "serial_number",
    "location": "location_text", "major category": "major_category", "category segments": "category_segment", "accounting date": "accounting_date",
    "date placed in service": "in_service", "prorate date": "prorate_date", "prorate convention code": "prorate_convention", "deprn start date": "deprn_start_date",
    "date retired": "date_retired", "asset type": "asset_type", "method code": "method_code", "life in months": "life_raw", "current units": "current_units",
    "current period": "current_period", "original cost": "original_cost", "adjusted cost": "adjusted_cost", "recoverable cost": "recoverable_cost", "cost": "cost",
    "ytd accu depreciation": "ytd_depreciation", "tal accu depreciation last": "accumulated_depreciation", "d net book value last": "net_book_value",
}
for m in MONTHS:
    HEADERS[f"{m} system deprn amount"] = "m_" + m
REQUIRED = ("asset_number", "description", "location_text", "major_category", "cost", "net_book_value")
_DMY = re.compile(r"^\s*(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s*$")


class UnrecognisedAssetRegister(ValueError):
    pass


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    count: int = 1
    examples: list[str] = field(default_factory=list)


@dataclass
class ParsedAssets:
    rows: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    sheet: str = ""

    def issue(self, code, severity, message, example=None, n=1):
        for i in self.issues:
            if i.code == code:
                i.count += n
                if example and len(i.examples) < 8:
                    i.examples.append(example)
                return
        self.issues.append(Issue(code, severity, message, n, [example] if example else []))


def _norm(h) -> str:
    return " ".join(str(h or "").lower().split())


def is_asset_register(content: bytes) -> bool:
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        row = next(wb.worksheets[0].iter_rows(max_row=1, values_only=True), ())
        names = {_norm(c) for c in row}
        return {"asset number", "major category", "original cost"} <= names
    except Exception:
        return False


def _dec(v):
    if v is None or v == "" or isinstance(v, bool):
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _txt(v):
    t = " ".join(str(v).replace("\xa0", " ").split()) if v is not None else ""
    return t or None


def _date(v):
    """(date | None, raw text | None): real dates pass; text is parsed only when day-first d-m-Y (unambiguous), and always kept as text too."""
    if isinstance(v, datetime):
        return v.date(), None
    if isinstance(v, date):
        return v, None
    if v in (None, ""):
        return None, None
    t = str(v).strip()
    m = _DMY.match(t)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))), t
        except ValueError:
            pass
    return None, t


def split_location(text: str | None):
    """'Governorate-City-Office-' -> its three parts, only when the text has exactly three '-' separated parts (else None: kept as written)."""
    if not text:
        return None
    parts = [p.strip() for p in text.strip().rstrip("-").split("-")]
    return tuple(parts) if len(parts) == 3 and all(parts) else None


def parse_assets(content: bytes) -> ParsedAssets:
    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.worksheets[0]
    head = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    cols = {i: HEADERS[_norm(h)] for i, h in enumerate(head) if _norm(h) in HEADERS}
    out = ParsedAssets(columns=[str(h) for h in head if h is not None], sheet=ws.title)
    missing = [f for f in REQUIRED if f not in cols.values()]
    if missing:
        raise UnrecognisedAssetRegister(f"Not an asset register export (columns not found: {', '.join(missing)})")
    unknown = [str(h) for i, h in enumerate(head) if h is not None and i not in cols]
    if unknown:
        out.issue("unknown_columns", "info", "Columns present in the file that this reader does not map (kept only in the stored original)", ", ".join(unknown[:6]), len(unknown))
    for rno, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        if all(v in (None, "") for v in row):
            continue
        r: dict = {"row_no": rno, "flags": [], "monthly_depreciation": {}}
        for i, f in cols.items():
            v = row[i] if i < len(row) else None
            if f.startswith("m_"):
                d = _dec(v)
                r["monthly_depreciation"][f[2:]] = str(d) if d is not None else None
            elif f in ("accounting_date", "prorate_date", "deprn_start_date", "date_retired", "current_period"):
                r[f] = _date(v)[0]
            elif f == "in_service":
                r["in_service_date"], r["in_service_raw"] = _date(v)
            elif f in ("original_cost", "adjusted_cost", "recoverable_cost", "cost", "ytd_depreciation", "accumulated_depreciation", "net_book_value", "current_units"):
                r[f] = _dec(v)
            elif f == "asset_number":
                r[f] = _txt(v)
            else:
                r[f] = _txt(v)
        if not r.get("asset_number"):
            out.issue("asset_number_missing", "critical", "A register row without an asset number (kept)", f"row {rno}")
            r["asset_number"] = ""
        parts = split_location(r.get("location_text"))
        if parts:
            r["location_governorate"], r["location_city"], r["location_office"] = parts
        elif r.get("location_text"):
            r["flags"].append("location_not_split")
        out.rows.append(r)
    if not out.rows:
        raise UnrecognisedAssetRegister("The register has no asset rows")
    _observe(out)
    return out


def _observe(p: ParsedAssets) -> None:
    rows = p.rows
    by_no: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_no[r["asset_number"]].append(r)
    for no, rs in by_no.items():
        if no and len(rs) > 1:
            for r in rs:
                r["flags"].append("duplicate_asset_number")
            p.issue("duplicate_asset_number", "critical", "The same asset number appears on more than one row (all kept)", f"{no} (rows {', '.join(str(r['row_no']) for r in rs)})", len(rs))
    period = Counter(r.get("current_period") for r in rows).most_common(1)[0][0]
    for r in rows:
        if r.get("in_service_raw"):
            r["flags"].append("in_service_date_is_text")
        if r.get("cost") is not None and r["cost"] <= 0:
            r["flags"].append("zero_or_negative_cost")
        if r.get("cost") is not None and r.get("original_cost") is not None and r["cost"] != r["original_cost"]:
            r["flags"].append("cost_differs_from_original")
        if None not in (r.get("cost"), r.get("accumulated_depreciation"), r.get("net_book_value")) and abs(r["cost"] - r["accumulated_depreciation"] - r["net_book_value"]) > Decimal("0.02"):
            r["flags"].append("nbv_not_cost_minus_accumulated")
        if r.get("accounting_date") and period and r["accounting_date"] > period:
            r["flags"].append("accounting_date_after_report_period")
        if r.get("in_service_date") and r.get("accounting_date") and r["accounting_date"] < r["in_service_date"]:
            r["flags"].append("accounting_before_in_service")
        if r.get("in_service_date") and period and r["in_service_date"] > period:
            r["flags"].append("in_service_after_report_period")
        ms = [Decimal(v) for v in r["monthly_depreciation"].values() if v is not None]
        if ms and r.get("ytd_depreciation") is not None and abs(sum(ms, ZERO) - r["ytd_depreciation"]) > Decimal("0.05"):
            r["flags"].append("ytd_not_sum_of_months")
        if r.get("serial_number") is None:
            r["flags"].append("no_serial_number")
    flag_text = {
        "in_service_date_is_text": ("warning", "The «Date Placed In Service» cell is text, not a date (kept as written; parsed day-first only where unambiguous)"),
        "zero_or_negative_cost": ("warning", "Asset with zero or negative cost"),
        "cost_differs_from_original": ("info", "«Cost» differs from «Original Cost»"),
        "nbv_not_cost_minus_accumulated": ("critical", "Net book value ≠ cost − accumulated depreciation"),
        "accounting_date_after_report_period": ("warning", "Accounting date later than the report's «Current Period»"),
        "accounting_before_in_service": ("warning", "Accounting date earlier than the in-service date"),
        "in_service_after_report_period": ("warning", "In-service date later than the report's «Current Period»"),
        "ytd_not_sum_of_months": ("info", "«Ytd Accu Depreciation» is not the sum of the monthly amounts shown (meaning of the difference not stated)"),
        "location_not_split": ("info", "Location text does not have the «Governorate-City-Office-» shape (kept as written)"),
    }
    cnt = Counter(f for r in rows for f in r["flags"])
    for code, (sev, msg) in flag_text.items():
        if cnt.get(code):
            ex = next((r["asset_number"] for r in rows if code in r["flags"]), None)
            p.issue(code, sev, msg, ex, cnt[code])
    n = len(rows)
    for fld, label in (("serial_number", "Serial Number"), ("tag_number", "Tag Number"), ("date_retired", "Date Retired")):
        filled = sum(1 for r in rows if r.get(fld) not in (None, ""))
        if filled < n:
            p.issue(f"{fld}_mostly_empty", "info", f"«{label}» is empty on {n - filled} of {n} rows (left empty, not filled in)", None, n - filled)
    for m in MONTHS:
        if all((r["monthly_depreciation"].get(m) in (None, "0", "0.0", "0.00")) for r in rows):
            p.issue("month_all_zero", "info", "A month's depreciation column is zero for every asset", m)


def profile(p: ParsedAssets) -> dict:
    rows = p.rows
    n = len(rows)
    s = lambda k: sum((r[k] for r in rows if r.get(k) is not None), ZERO)  # noqa: E731

    def group(keyf, top=None):
        d: dict = {}
        for r in rows:
            k = keyf(r) or None
            c = d.setdefault(k, {"key": k, "n": 0, "cost": ZERO, "nbv": ZERO})
            c["n"] += 1
            c["cost"] += r.get("cost") or ZERO
            c["nbv"] += r.get("net_book_value") or ZERO
        out = sorted(d.values(), key=lambda c: (-c["cost"], str(c["key"])))
        return [{**c, "cost": str(c["cost"]), "nbv": str(c["nbv"])} for c in (out[:top] if top else out)]
    period = Counter(r.get("current_period") for r in rows).most_common(1)[0][0]
    acc = [r["accounting_date"] for r in rows if r.get("accounting_date")]
    ins = [r["in_service_date"] for r in rows if r.get("in_service_date")]
    locations = {r["location_text"] for r in rows if r.get("location_text")}
    return {"rows": n, "columns": p.columns, "current_period": period.isoformat() if period else None,
            "totals": {k: str(s(k)) for k in ("original_cost", "adjusted_cost", "recoverable_cost", "cost", "ytd_depreciation", "accumulated_depreciation", "net_book_value")},
            "units_total": str(s("current_units")), "assets_with_multiple_units": sum(1 for r in rows if (r.get("current_units") or 0) > 1),
            "distinct_asset_numbers": len({r["asset_number"] for r in rows}),
            "asset_number_range": [min((int(r["asset_number"]) for r in rows if r["asset_number"].isdigit()), default=None), max((int(r["asset_number"]) for r in rows if r["asset_number"].isdigit()), default=None)],
            "by_segment": group(lambda r: r.get("category_segment")), "by_major_category": group(lambda r: r.get("major_category"), 60),
            "by_governorate": group(lambda r: r.get("location_governorate") or "(not split)"), "locations": len(locations),
            "head_office_assets": sum(1 for r in rows if "head office" in (r.get("location_text") or "").lower()),
            "in_service_years": dict(sorted(Counter(str(d.year) for d in ins).items())), "in_service_range": [min(ins).isoformat(), max(ins).isoformat()] if ins else None,
            "accounting_range": [min(acc).isoformat(), max(acc).isoformat()] if acc else None,
            "life_values": dict(Counter(r.get("life_raw") for r in rows)), "fully_depreciated_nbv_le_1": sum(1 for r in rows if (r.get("net_book_value") or 0) <= 1),
            "monthly_depreciation_totals": {m: str(sum((Decimal(r["monthly_depreciation"][m]) for r in rows if r["monthly_depreciation"].get(m) is not None), ZERO)) for m in MONTHS},
            "issues": [{"code": i.code, "severity": i.severity, "message": i.message, "count": i.count, "examples": i.examples} for i in p.issues]}


def diff(old: dict[str, list[dict]], new: dict[str, list[dict]]) -> dict:
    """Version-to-version difference by asset number (no inference: added / removed / changed fields only)."""
    fields = ("description", "location_text", "major_category", "category_segment", "cost", "net_book_value", "current_units", "date_retired")
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed: dict[str, int] = Counter()
    examples: dict[str, list] = defaultdict(list)
    for no in set(old) & set(new):
        o, n = old[no][0], new[no][0]
        for f in fields:
            if str(o.get(f)) != str(n.get(f)):
                changed[f] += 1
                if len(examples[f]) < 5:
                    examples[f].append(no)
    return {"added": len(added), "removed": len(removed), "added_examples": added[:10], "removed_examples": removed[:10], "changed_by_field": dict(changed),
            "changed_examples": dict(examples), "in_both": len(set(old) & set(new))}
