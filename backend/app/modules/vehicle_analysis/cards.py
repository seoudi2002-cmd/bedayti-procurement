"""Readers for the two per-vehicle monthly files:
* the vehicle usage report (تقرير عن تنظيم استخدام السيارات): a daily odometer log (start / end / distance), fuel taken and oil changes;
* the maintenance card (كارت صيانة السيارات): current odometer and, for each service item, the previous and next-due readings and the km remaining.

Read as stated, never fixed: a card month whose odometer is 0 is an unfilled template row, not a reading; the usage report's stated totals are kept
and compared with the sum of its daily rows."""
import re
from dataclasses import dataclass, field

from app.core.analysis.opsupport import Issues, fold, month_in_text, num, period_str
from app.modules.vehicle_analysis import plates
from app.modules.vehicle_analysis.grid import Grid, excel_date

_CARD_DATE = re.compile(r"(20\d{2})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})")


class NotACard(Exception):
    pass


@dataclass
class Rec:
    plate: str
    plate_key: str
    period: str
    ref: str
    values: dict
    personal: dict = field(default_factory=dict)
    vtype: str | None = None


@dataclass
class Parsed:
    kind: str = ""
    rows: list = field(default_factory=list)
    periods: list = field(default_factory=list)
    skipped: list = field(default_factory=list)        # periods of unfilled template sheets
    issues: Issues = field(default_factory=Issues)


def is_usage(gs: list[Grid]) -> bool:
    return any("تنظيم استخدام السيارات" in fold(g.text(r, c)) for g in gs[:3] for r in range(min(g.nrows, 6)) for c in range(min(g.ncols, 6)))


def is_card(gs: list[Grid]) -> bool:
    return any("كارت صيانه" in fold(g.text(r, 0)) for g in gs[:3] for r in range(min(g.nrows, 8)))


def parse_usage(gs: list[Grid], filename: str) -> Parsed:
    p = Parsed(kind="usage_report")
    for g in gs:
        if g.hidden:
            continue
        r_title = next((r for r in range(min(g.nrows, 6)) if "تنظيم استخدام" in fold(g.text(r, 2)) or "تنظيم استخدام" in fold(g.text(r, 0))), None)
        if r_title is None:
            continue
        d = next((excel_date(g.v(r_title, c), g.datemode) for c in range(g.ncols) if excel_date(g.v(r_title, c), g.datemode)), None)
        sm, _ = month_in_text(g.title)
        if d is None:
            p.issues.add("period_unreadable", "warning", "A usage sheet with no readable date (not read)", g.title)
            continue
        period = period_str(d.year, sm if sm is not None else d.month)
        if sm is not None and sm != d.month:
            p.issues.add("sheet_name_date_mismatch", "warning", "A sheet's name and the date written in it differ (the sheet name is used for the month; the date cell only moves by one day from sheet to sheet)", f"{g.title.strip()} / {d}")
        r_car = next((r for r in range(r_title, min(g.nrows, r_title + 10)) if "ماركه السياره" in fold(g.text(r, 0)) or "رقم السياره" in fold(g.text(r, 3))), None)
        if r_car is None:
            p.issues.add("sheet_unrecognised", "info", "A usage sheet without the vehicle line (not read)", g.title)
            continue
        plate = plates.clean(g.v(r_car, 4)) or ""
        brand = g.text(r_car, 0).split("/", 1)[-1].strip()
        # stated header figures: label in col 2, value in col 6
        hv = {}
        for r in range(r_title + 1, r_car):
            lab = fold(g.text(r, 2))
            if "اجمالي المسافه" in lab:
                hv["km_total"] = num(g.v(r, 6))
            elif "كميه الوقود" in lab:
                hv["fuel_qty"] = num(g.v(r, 6))
            elif "معدل استهلاك" in lab:
                hv["consumption_stated"] = num(g.v(r, 6))
            elif "تغيير الزيت" in lab:
                hv["oil_changes_stated"] = num(g.v(r, 6))
        r_h = next((r for r in range(r_car, min(g.nrows, r_car + 6)) if fold(g.text(r, 0)) == "الايام"), None)
        if r_h is None:
            p.issues.add("sheet_unrecognised", "info", "A usage sheet without the daily table (not read)", g.title)
            continue
        days = km = 0
        odo_start = odo_end = None
        refuels = 0
        notes = []
        foot = None
        daily_sum = 0.0
        for r in range(r_h + 2, g.nrows):
            a = g.v(r, 0)
            if isinstance(a, (int, float)):
                k = num(g.v(r, 3)) or 0.0
                daily_sum += k
                if k > 0:
                    days += 1
                s, e = num(g.v(r, 1)), num(g.v(r, 2))
                if s and odo_start is None:
                    odo_start = s
                if e:
                    odo_end = max(odo_end or 0, e)
                if num(g.v(r, 8)) is not None:
                    refuels += 1
                if g.text(r, 11):
                    notes.append(g.text(r, 11))
            elif a is None and num(g.v(r, 3)) is not None:
                foot = num(g.v(r, 3))
        vals = {"km_daily_sum": round(daily_sum, 3), "days_used": days, "refuel_events": refuels, **{k: v for k, v in hv.items() if v is not None}}
        if foot is not None:
            vals["km_footer"] = foot
        if odo_start is not None:
            vals["odometer_first"] = odo_start
        if odo_end is not None:
            vals["odometer_last"] = odo_end
        if "km_total" in vals and abs(vals["km_total"] - daily_sum) > 0.5:
            p.issues.add("km_total_differs_from_days", "warning", "A stated monthly distance that differs from the sum of the daily rows (the stated figure is kept)", f"{g.title}: {vals['km_total']:g} vs {daily_sum:g}")
        if vals.get("km_total") and vals.get("fuel_qty") and vals.get("consumption_stated") is not None:
            calc = vals["km_total"] / vals["fuel_qty"]
            if abs(calc - vals["consumption_stated"]) > 0.01 * max(calc, 1):
                p.issues.add("consumption_differs_from_km_over_fuel", "warning", "A stated consumption rate that is not km ÷ fuel (the stated figure is kept; the computed one is shown)", f"{g.title}: {vals['consumption_stated']:g} vs {calc:.2f}")
        p.rows.append(Rec(plate=plate, plate_key=plates.key(plate), period=period, ref=f"{g.title}!{r_car + 1}", values=vals, personal={"notes": " | ".join(notes)} if notes else {}, vtype=brand or None))
    if not p.rows:
        raise NotACard()
    p.periods = sorted({r.period for r in p.rows})
    return p


def parse_card(gs: list[Grid], filename: str) -> Parsed:
    p = Parsed(kind="maintenance_card")
    for g in gs:
        if g.hidden:
            continue
        r_t = next((r for r in range(min(g.nrows, 8)) if "كارت صيانه" in fold(g.text(r, 0))), None)
        if r_t is None:
            continue
        mm = _CARD_DATE.search(g.text(r_t, 0))
        if not mm:
            p.issues.add("period_unreadable", "warning", "A maintenance-card sheet whose title carries no date (not read)", g.title)
            continue
        period = period_str(int(mm.group(1)), int(mm.group(2)))
        sm, _ = month_in_text(g.title)
        if sm is not None and sm != int(mm.group(2)):
            p.issues.add("sheet_name_date_mismatch", "warning", "A sheet's name and the date written in its title differ (the date is used)", f"{g.title} / {mm.group(0)}")
        r_h = next((r for r in range(r_t, min(g.nrows, r_t + 6)) if "رقم السياره" in fold(g.text(r, 1))), None)
        if r_h is None:
            p.issues.add("sheet_unrecognised", "info", "A maintenance-card sheet without the header row (not read)", g.title)
            continue
        items = {c: g.text(r_h, c) for c in range(5, g.ncols) if g.text(r_h, c) and "ملاحظ" not in fold(g.text(r_h, c))}
        filled = 0
        for r in range(r_h + 2, g.nrows):
            if not isinstance(g.v(r, 0), (int, float)) or g.v(r, 1) is None:
                continue
            plate = plates.clean(g.v(r, 1))
            km = num(g.v(r, 4))
            if not km:
                continue            # km 0 / blank: an unfilled template row for a month not yet recorded
            vals = {"odometer": km}
            for c, name in items.items():
                prev, nxt, rem = num(g.v(r, c)), num(g.v(r, c + 1)), num(g.v(r, c + 2))
                for tag, v in (("previous", prev), ("next_due", nxt), ("remaining", rem)):
                    if v is not None:
                        vals[f"svc:{name}:{tag}"] = v
            note = g.text(r, 35) if g.ncols > 35 else ""
            if note:
                vals["note"] = note
            driver = g.text(r, 3)
            p.rows.append(Rec(plate=plate, plate_key=plates.key(plate), period=period, ref=f"{g.title}!{r + 1}", values=vals, personal={"driver": driver} if driver else {}, vtype=g.text(r, 2) or None))
            filled += 1
        if not filled:
            p.skipped.append(period)
    if p.skipped:
        p.issues.add("template_months_not_recorded", "info", "Card sheets with no odometer reading (unfilled months; not counted as zero)", ", ".join(sorted(set(p.skipped))))
    if not p.rows:
        raise NotACard()
    p.periods = sorted({r.period for r in p.rows})
    return p
