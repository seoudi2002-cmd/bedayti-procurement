"""Reader for the monthly vehicle repairs statement (بيان الاصلاحات): one sheet per month, one row per vehicle, cost categories in columns,
then the stated maintenance total, fuel cost, fuel quantity, grand total and distance. A half-year sheet adds the months by formula and
carries a small insurance-claim table.

Read as stated, never fixed: columns are found by header text per sheet (they move between months); stated totals are kept and compared with
the sum of their parts; the fuel quantity is read together with the price in its own formula (=cost/price) because it is derived, not measured."""
import re
from dataclasses import dataclass, field

from app.core.analysis.opsupport import Issues, fold, month_in_text, num, period_str
from app.modules.vehicle_analysis import plates
from app.modules.vehicle_analysis.grid import Grid

_QTY = re.compile(r"^=\s*\$?[A-Z]{1,3}\$?\d+\s*/\s*\(?([\d.]+)\)?\s*$")


class NotRepairs(Exception):
    pass


@dataclass
class CostRow:
    plate: str
    plate_key: str
    vtype: str
    period: str
    ref: str
    values: dict = field(default_factory=dict)
    note: str | None = None


@dataclass
class Parsed:
    rows: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    controls: list = field(default_factory=list)       # per month: stated total row vs sum of vehicle rows
    halfyear: list = field(default_factory=list)       # per vehicle: half-year sheet total vs sum of months
    periods: list = field(default_factory=list)
    prices: dict = field(default_factory=dict)         # period -> sorted prices found in qty formulas
    year: int | None = None
    year_source: str | None = None
    issues: Issues = field(default_factory=Issues)


def is_repairs(gs: list[Grid]) -> bool:
    for g in gs:
        for r in range(min(g.nrows, 6)):
            t = " ".join(fold(x) for x in g.row_texts(r).values())
            if ("اجمالي" in t and "الصيان" in t and "الوقود" in t) or ("الصيانات" in t and "الوقود" in t):
                return True
    return False


def _find(texts: dict, *tokens):
    return next((c for c, t in texts.items() if all(x in fold(t) for x in tokens)), None)


def parse(gs: list[Grid], year: int | None, filename: str) -> Parsed:
    p = Parsed()
    half = next((g for g in gs if "نصف" in fold(g.title) or "اجمالي" in fold(g.title)), None)
    if half is not None:
        _m, y = month_in_text(half.title)
        if y:
            p.year, p.year_source = y, "other_sheets"
    if p.year is None:
        from collections import Counter
        ys = Counter(month_in_text(g.text(0, 0))[1] for g in gs if not g.hidden and g is not half and month_in_text(g.text(0, 0))[1])
        if ys:
            p.year, p.year_source = ys.most_common(1)[0][0], "sheet_title"
    if p.year is None and year:
        p.year, p.year_source = year, "uploader"
    if p.year is None:
        ym = re.search(r"(20\d{2})", filename)
        if ym:
            p.year, p.year_source = int(ym.group(1)), "filename"
            p.issues.add("year_from_filename", "info", "The statement's sheets carry no year; the year in the file name was used", ym.group(1))
    if p.year is None:
        raise NotRepairs()
    month_sheets = []
    for g in gs:
        if g.hidden or g is half:
            continue
        m, _y = month_in_text(g.title)
        if m is None:
            continue
        month_sheets.append((g, m))
    for g, m in month_sheets:
        tm, _ty = month_in_text(g.text(0, 0))
        if tm is not None and tm != m:
            p.issues.add("sheet_name_title_mismatch", "warning", "A sheet's name and the month written in its title differ (the name is used)", f"{g.title.strip()} / {g.text(0, 0)[:40]}")
        _sheet(g, m, p)
    if half is not None:
        _half(half, p)
    p.periods = sorted({r.period for r in p.rows})
    if not p.rows:
        raise NotRepairs()
    by: dict = {}
    for r in p.rows:
        by.setdefault(r.plate_key, {})[r.period] = r
    for k, d in by.items():
        for a, b in zip(sorted(d), sorted(d)[1:]):
            ka, kb = d[a].values.get("km"), d[b].values.get("km")
            if ka and kb and ka == kb:
                p.issues.add("km_same_as_previous_month", "warning", "A vehicle's distance identical to the previous month's (possibly carried over rather than recorded)", f"{d[b].plate}: {b} = {a} ({kb:g})")
    return p


def _sheet(g: Grid, m: int, p: Parsed):
    period = period_str(p.year, m)
    hr = next((r for r in range(min(g.nrows, 6)) if _find(g.row_texts(r), "اجمالي", "الصيان")), None)
    if hr is None:
        p.issues.add("sheet_unrecognised", "info", "A month sheet without the cost-total header (not read)", g.title)
        return
    t2 = g.row_texts(hr)
    c_maint = _find(t2, "اجمالي", "الصيان")
    c_fuel = next((c for c, t in t2.items() if "الوقود" in fold(t) and "كميه" not in fold(t) and "اجمالي" in fold(t)), None)
    c_qty, c_grand, c_km = _find(t2, "كميه", "الوقود"), _find(t2, "الاجمالى", "العام") or _find(t2, "الاجمالي", "العام"), _find(t2, "المسافه")
    c_start = _find(t2, "الصيانات")
    c_notes = [c for c, t in t2.items() if "ملاحظات" in fold(t)]
    c_type = _find(t2, "نوع", "السياره")
    if None in (c_maint, c_fuel, c_qty, c_grand, c_start):
        p.issues.add("sheet_unrecognised", "info", "A month sheet missing one of the stated-total columns (not read)", g.title)
        return
    # category columns: from the first cost column up to the maintenance total; labels from the two header rows below
    cats = {}
    for c in range(c_start, c_maint):
        top, sub = g.group_fill(hr + 1, c), g.text(hr + 2, c)
        label = " - ".join(x for x in (top, sub) if x) or (g.text(hr, c) if c > c_start else "")
        if label:
            cats[c] = label
    extra = {c: " - ".join(x for x in (g.group_fill(hr + 1, c), g.text(hr + 2, c)) if x) for c in range(c_fuel + 1, c_qty) if g.group_fill(hr + 1, c) or g.text(hr + 2, c)}
    plate_col = 1
    first = hr + 3
    rows = []
    stated_total = None
    total_row = None
    for r in range(first, g.nrows):
        a = g.v(r, 0)
        plate_txt = plates.clean(g.v(r, plate_col))
        if isinstance(a, (int, float)) and plate_txt:
            rows.append(r)
            continue
        if rows and a is None and not plate_txt:
            gr = num(g.v(r, c_grand))
            if gr is not None and total_row is None:
                stated_total, total_row = gr, r
    for r in rows:
        plate_txt = plates.clean(g.v(r, plate_col))
        vals = {}
        for c, label in cats.items():
            n = num(g.v(r, c))
            if n is not None:
                vals[f"cat:{label}"] = n
        for k, c in (("maint_total", c_maint), ("fuel_cost", c_fuel), ("fuel_qty", c_qty), ("grand_total", c_grand), ("km", c_km)):
            if c is not None and num(g.v(r, c)) is not None:
                vals[k] = num(g.v(r, c))
        if c_km is not None and g.v(r, c_km) is not None and num(g.v(r, c_km)) is None:
            p.issues.add("km_not_numeric", "info", "A distance cell that is not a plain number (ignored)", f"{g.title}!{r + 1}: {g.v(r, c_km)}")
        fq = g.formula(r, c_qty)
        if fq:
            mm = _QTY.match(fq.replace(" ", ""))
            if mm:
                vals["fuel_price_in_formula"] = float(mm.group(1))
                p.prices.setdefault(period, set()).add(float(mm.group(1)))
        elif "fuel_qty" in vals and g.nrows:
            pass
        for c, label in extra.items():
            n = num(g.v(r, c))
            if n:
                p.issues.add("extra_column_not_counted", "info", "A cost column outside the stated totals that holds a value (kept out of the totals)", f"{g.title}!{label}")
        note = " | ".join(g.text(r, c) for c in c_notes if g.text(r, c)) or None
        vt = g.text(r, c_type) if c_type is not None else g.text(r, 2)
        if vt:
            vals["type"] = vt
        cats_sum = sum(v for k, v in vals.items() if k.startswith("cat:"))
        mt, ft, gt = vals.get("maint_total"), vals.get("fuel_cost"), vals.get("grand_total")
        if mt is not None and any(k.startswith("cat:") for k in vals) and abs(cats_sum - mt) > 0.01:
            p.issues.add("maintenance_total_differs_from_categories", "warning", "A stated maintenance total that differs from the sum of its category cells (the stated total is kept)", f"{g.title}!{r + 1}")
        if mt is not None and ft is not None and gt is not None and abs(mt + ft - gt) > 0.01:
            p.issues.add("grand_total_differs_from_parts", "warning", "A stated grand total that differs from maintenance + fuel (the stated total is kept)", f"{g.title}!{r + 1}")
        p.rows.append(CostRow(plate=plate_txt, plate_key=plates.key(plate_txt), vtype=vt, period=period, ref=f"{g.title.strip()}!{r + 1}", values=vals, note=note))
    comp = sum(num(g.v(r, c_grand)) or 0 for r in rows)
    p.controls.append({"period": period, "sheet": g.title.strip(), "stated": stated_total, "computed": round(comp, 2), "diff": round((stated_total or 0) - comp, 2) if stated_total is not None else None})
    if stated_total is None:
        p.issues.add("no_total_row", "info", "A month sheet with no total row to compare against", g.title)
    elif abs(stated_total - comp) > 0.01:
        p.issues.add("total_row_differs", "warning", "A month's stated total row differs from the sum of its vehicle rows (shown in the controls; the vehicle rows are used)", f"{g.title.strip()}: {stated_total:,.2f} vs {comp:,.2f}")


def _half(g: Grid, p: Parsed):
    """Half-year sheet: per vehicle totals (compared with the sum of the months) and the insurance-claim side table."""
    hr = next((r for r in range(min(g.nrows, 6)) if _find(g.row_texts(r), "الاجمالي", "العام")), None)
    if hr is not None:
        t = g.row_texts(hr)
        c_grand = _find(t, "الاجمالي", "العام")
        if c_grand is not None:
            by_key: dict[str, float] = {}
            for r in p.rows:
                by_key[r.plate_key] = by_key.get(r.plate_key, 0.0) + (r.values.get("grand_total") or 0.0)
            for r in range(hr + 1, g.nrows):
                pl = plates.clean(g.v(r, 1))
                st = num(g.v(r, c_grand))
                if pl and st is not None and isinstance(g.v(r, 0), (int, float)):
                    comp = by_key.get(plates.key(pl))
                    p.halfyear.append({"plate": pl, "stated": st, "computed": round(comp, 2) if comp is not None else None, "diff": round(st - comp, 2) if comp is not None else None})
            for r in range(hr + 1, g.nrows):
                if g.v(r, 0) is None and not plates.clean(g.v(r, 1)) and num(g.v(r, c_grand)) is not None:
                    allc = sum(x["computed"] or 0 for x in p.halfyear)
                    p.halfyear.append({"plate": None, "stated": num(g.v(r, c_grand)), "computed": round(sum(sum(row.values.get("grand_total") or 0 for row in p.rows) for _ in [0]), 2), "diff": None})
                    p.halfyear[-1]["diff"] = round(p.halfyear[-1]["stated"] - p.halfyear[-1]["computed"], 2)
                    if abs(p.halfyear[-1]["diff"]) > 0.01:
                        p.issues.add("halfyear_total_differs", "warning", "The half-year sheet's stated total differs from the sum of the month sheets read", f"{p.halfyear[-1]['stated']:,.2f} vs {p.halfyear[-1]['computed']:,.2f}")
                    break
    # insurance side table: header cell with «تحت حساب التأمين»
    for r in range(min(g.nrows, 8)):
        for c in range(g.ncols):
            if "تحت حساب التامين" in fold(g.v(r, c)):
                _claims(g, r, c, p)
                return


def _claims(g: Grid, r0: int, c0: int, p: Parsed):
    hdr = {c: fold(g.v(r0, c)) for c in range(c0, g.ncols) if g.v(r0, c) is not None}
    c_month = _find(hdr, "الشهر")
    c_orig = _find(hdr, "اصل")
    c_ins = _find(hdr, "تحمل", "التامين")
    c_co = _find(hdr, "تحمل", "الشركه")
    for r in range(r0 + 1, g.nrows):
        desc = g.text(r, c0)
        if not desc:
            continue
        m, _y = month_in_text(g.v(r, c_month)) if c_month is not None else (None, None)
        vals = {"original": num(g.v(r, c_orig)) if c_orig is not None else None, "insurer_share": num(g.v(r, c_ins)) if c_ins is not None else None,
                "company_share": num(g.v(r, c_co)) if c_co is not None else None}
        note = " ".join(g.text(r, c) for c in range((c_co or c0) + 1, g.ncols) if g.text(r, c))
        p.claims.append({"desc": desc, "period": period_str(p.year, m) if m else None, "values": {k: v for k, v in vals.items() if v is not None}, "note": note or None, "ref": f"{g.title}!{r + 1}"})
