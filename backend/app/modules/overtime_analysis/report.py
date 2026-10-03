"""ReportModel for overtime analytics. Hours only: no amounts, salary or attendance exist in the statement, so none are shown or estimated."""
from datetime import datetime, timezone

from app.core.analysis.opreport import C as BaseC, merged_issues, quality_section, versions_section
from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, pct, period_label, spct

T = {
    "ar": {
        "title": "تحليل الأجر الإضافي (الساعات والمأموريات والوجبات)", "s_summary": "الملخص التنفيذي", "s_monthly": "الاتجاه الشهري", "s_employees": "حسب الموظف", "s_annual": "التراكم السنوي",
        "filtered": "عرض مفلتر", "hours": "ساعة", "k_hours": "ساعات الشهر (نهاري + ليلي)", "k_weighted": "الساعات المكافئة (كما في الكشف)", "k_day": "نهاري", "k_night": "ليلي", "k_active": "موظفون لهم إضافي",
        "k_meals": "الوجبات", "k_missions": "المأموريات", "k_ytd": "تراكم {y} حتى الآن", "k_avg": "متوسط الساعات للموظف", "k_conc": "نسبة أعلى {n} موظفين", "k_nights": "نسبة الليلي",
        "c_period": "الشهر", "c_hours": "الساعات", "c_day": "نهاري", "c_night": "ليلي", "c_weighted": "المكافئة", "c_d": "تغير المكافئة", "c_dpct": "التغير %", "c_listed": "في الكشف", "c_entries": "بإدخال",
        "c_active": "لهم إضافي", "c_meals": "وجبات", "c_mday": "مأموريات نهاري", "c_mnight": "مأموريات ليلي", "c_note": "ملاحظة", "c_code": "الكود", "c_name": "الاسم", "c_months": "أشهر بإدخال",
        "c_avg": "متوسط الشهر", "c_max": "أعلى شهر", "c_share": "النسبة %", "c_cum": "التراكمي %", "c_cur": "الشهر الحالي", "c_missions": "المأموريات", "c_year": "السنة", "c_mcount": "الأشهر",
        "c_factor": "المضاعف", "c_nightsh": "الليلي %", "c_peremp": "متوسط للموظف",
        "t_months": "المؤشرات الشهرية", "t_emp": "الموظفون (التراكم حتى آخر شهر)", "t_heat": "الموظف × الشهر (ساعات)", "t_high": "أشهر أعلى كثيرًا من متوسط الموظف نفسه", "t_years": "الإجمالي السنوي (من الأشهر المتاحة)",
        "ch_month": "الساعات الشهرية: نهاري وليلي", "ch_top": "أعلى الموظفين ساعات (تراكميًا)", "ch_heat": "خريطة حرارية: الموظف × الشهر",
        "large": "تغير كبير", "na": "غير متاح", "not_avail": "لا يوجد كشف لهذا الشهر",
        "x_cur": "{m}: {h} ساعة (نهاري {d}، ليلي {n})، مكافئة {w}، لـ {a} موظف، {ml} وجبة و{ms} مأمورية.", "x_mom": "التغير في الساعات المكافئة عن {p}: {pc}.", "x_ytd": "تراكم {y} ({n} شهرًا متاحًا): {h} ساعة، مكافئة {w}.",
        "x_peak": "أعلى شهر ساعات {pm} ({ph}) وأقلها {lm} ({lh}).", "x_conc": "أعلى {k} موظفين يمثلون {c} من الساعات التراكمية.", "x_night": "نسبة الليلي من ساعات {m}: {s}.",
        "x_missing": "أشهر بلا كشف في الملف: {m}؛ لا تُقدَّر ولا تُحتسب صفرًا.", "x_empty": "{n} صفوف لموظفين مذكورين في الكشف بلا إدخال في الشهر (لا إدخال، وليست صفرًا).",
        "x_high": "{n} حالة (موظف-شهر) أعلى من {f}× متوسط الموظف نفسه.",
        "i_basis": "الكميات ساعات كما في الكشف؛ «المكافئة» هي القيمة الموزونة التي يحسبها الكشف نفسه (نهاري ×{d}، ليلي ×{n}). لا توجد مبالغ أو قيمة ساعة، فلا تُحوَّل إلى تكلفة. ولا تحليل حضور وانصراف.",
        "i_basis_nofac": "الكميات ساعات كما في الكشف؛ «المكافئة» هي القيمة الموزونة المذكورة فيه. لا توجد مبالغ أو قيمة ساعة، فلا تُحوَّل إلى تكلفة. ولا تحليل حضور وانصراف.",
        "i_period": "الفترة تؤخذ من العنوان المكتوب داخل كل ورقة وليس من اسم الورقة.", "i_filtered": "العرض مفلتر على الموظفين المختارين.", "i_focus": "لقطة حتى {m}.",
        "na_money": "التكلفة المالية للأوفر تايم: لا توجد قيمة ساعة أو مبالغ في الملف", "na_attendance": "الحضور والانصراف ومواعيد العمل: غير موجودة (ولا تُبنى عليها أي نتيجة)", "na_dept": "القسم أو الفرع للموظف وسبب الإضافي: غير مذكور",
        "n_personal": "أسماء الموظفين بيانات شخصية: تظهر للمدير فقط؛ يُعرض الكود لغيره.", "f_emp": "الموظف", "t_controls": "مطابقة إجمالي الورقة السنوية بمجموع الأشهر المقروءة", "ctl_note": "الفرق يظهر عندما تحتوي ورقة الإجمالي على شهر مكرر أو لا تطابق الأشهر؛ يُعرض ولا يُصحَّح.",
        "c_field": "الحقل", "c_stated": "المذكور في الملف", "c_computed": "المحسوب من الأشهر", "c_diff": "الفرق",
        "fld_mission_day": "مأموريات نهاري", "fld_mission_night": "مأموريات ليلي", "fld_meals": "وجبات", "fld_day_hours": "ساعات نهاري", "fld_day_weighted": "نهاري مكافئ", "fld_night_hours": "ساعات ليلي",
        "fld_night_weighted": "ليلي مكافئ", "fld_raw_total": "إجمالي الساعات", "fld_weighted_total": "إجمالي مكافئ", "fld_equal_pay_days": "مثل الأجر", "fld_equal_pay_x2": "الإجمالي × 2", "fld_listed": "مدرج",
    },
    "en": {
        "title": "Overtime analysis (hours, missions and meals)", "s_summary": "Executive summary", "s_monthly": "Monthly trend", "s_employees": "By employee", "s_annual": "Annual cumulative",
        "filtered": "Filtered view", "hours": "h", "k_hours": "Hours this month (day + night)", "k_weighted": "Weighted hours (as the statement computes them)", "k_day": "Day", "k_night": "Night", "k_active": "Employees with overtime",
        "k_meals": "Meals", "k_missions": "Missions", "k_ytd": "{y} to date", "k_avg": "Average hours per employee", "k_conc": "Top {n} employees' share", "k_nights": "Night share",
        "c_period": "Month", "c_hours": "Hours", "c_day": "Day", "c_night": "Night", "c_weighted": "Weighted", "c_d": "Weighted change", "c_dpct": "Change %", "c_listed": "Listed", "c_entries": "With an entry",
        "c_active": "With overtime", "c_meals": "Meals", "c_mday": "Day missions", "c_mnight": "Night missions", "c_note": "Note", "c_code": "Code", "c_name": "Name", "c_months": "Months with entries",
        "c_avg": "Monthly average", "c_max": "Highest month", "c_share": "Share %", "c_cum": "Cumulative %", "c_cur": "Current month", "c_missions": "Missions", "c_year": "Year", "c_mcount": "Months",
        "c_factor": "Multiple", "c_nightsh": "Night %", "c_peremp": "Average per employee",
        "t_months": "Monthly figures", "t_emp": "Employees (cumulative to the last month)", "t_heat": "Employee × month (hours)", "t_high": "Months far above the employee's own average", "t_years": "Annual total (from the available months)",
        "ch_month": "Monthly hours: day and night", "ch_top": "Top employees by hours (cumulative)", "ch_heat": "Heatmap: employee × month",
        "large": "Large change", "na": "n/a", "not_avail": "No statement for this month",
        "x_cur": "{m}: {h} h (day {d}, night {n}), weighted {w}, for {a} employees, {ml} meals and {ms} missions.", "x_mom": "Change in weighted hours vs {p}: {pc}.", "x_ytd": "{y} to date ({n} months available): {h} h, weighted {w}.",
        "x_peak": "Highest month {pm} ({ph}) and lowest {lm} ({lh}).", "x_conc": "The top {k} employees account for {c} of cumulative hours.", "x_night": "Night share of {m} hours: {s}.",
        "x_missing": "Months with no statement in the file: {m}; not estimated and not counted as zero.", "x_empty": "{n} rows of employees listed in the statement have no entry for the month (no entry, not zero).",
        "x_high": "{n} employee-months are above {f}× the employee's own average.",
        "i_basis": "Quantities are hours as in the statement; «weighted» is the statement's own weighted value (day ×{d}, night ×{n}). There are no amounts or hourly rate, so nothing is converted to cost; no attendance analysis.",
        "i_basis_nofac": "Quantities are hours as in the statement; «weighted» is the statement's own weighted value. There are no amounts or hourly rate, so nothing is converted to cost; no attendance analysis.",
        "i_period": "The period is taken from the title written inside each sheet, not from the sheet name.", "i_filtered": "Filtered to the selected employees.", "i_focus": "Snapshot up to {m}.",
        "na_money": "Cost of the overtime: the file has no hourly rate or amounts", "na_attendance": "Attendance and working hours: not present (nothing is concluded from them)", "na_dept": "Employee department / branch and the reason for overtime: not stated",
        "n_personal": "Employee names are personal data: shown to admins only; others see the code.", "f_emp": "Employee", "t_controls": "The annual sheet's totals against the sum of the months read", "ctl_note": "A difference appears when the annual sheet includes a repeated month or does not match the months; shown, not corrected.",
        "c_field": "Field", "c_stated": "Stated in the file", "c_computed": "Computed from the months", "c_diff": "Difference",
        "fld_mission_day": "Day missions", "fld_mission_night": "Night missions", "fld_meals": "Meals", "fld_day_hours": "Day hours", "fld_day_weighted": "Day weighted", "fld_night_hours": "Night hours",
        "fld_night_weighted": "Night weighted", "fld_raw_total": "Total hours", "fld_weighted_total": "Weighted total", "fld_equal_pay_days": "Equal-pay days", "fld_equal_pay_x2": "Total × 2", "fld_listed": "Listed",
    },
}


class C(BaseC):
    def __init__(self, lang):
        super().__init__(lang, T)


def _g(v, d=1):
    return "—" if v is None else f"{v:,.{d}f}"


def build_report(a: dict, data: dict, th: dict, th_origin: dict, lang: str, filters: dict, dims: list[dict], admin: bool, focus: str | None) -> ReportModel:
    c = C(lang)
    t = a["totals"]
    cur = t["cur"]
    L = lambda p: period_label(lang, (int(p[:4]), int(p[5:7])))
    S = lambda p: period_label(lang, (int(p[:4]), int(p[5:7])), True)
    who = lambda e: (e["name"] or e["code"]) if admin else e["code"]
    files = [v["file"] for v in data["versions"]]
    rm = ReportModel(title=c.t("title"), period_label=f"{L(a['periods'][0])} – {L(a['periods'][-1])}", sections=[], lang=lang)
    rm.subtitle = " · ".join(files[-3:]) + (" · " + c.t("filtered") if a["filtered"] else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(files[-3:]), "file_hash": "", "filters": {"active": filters, "options": {}, "dimensions": dims}}
    factors = next((s["factors"] for s in reversed(data["summaries"]) if s.get("factors")), None)

    items = [{"metric": "cur", "text": c.t("x_cur", m=L(cur["period"]), h=_g(cur["hours"]), d=_g(cur["day_hours"]), n=_g(cur["night_hours"]), w=_g(cur["weighted"]), a=cur["active"], ml=f"{cur['meals']:,.0f}", ms=f"{cur['mission_day'] + cur['mission_night']:,.0f}")}]
    if cur.get("dpct") is not None:
        pm = a["avail"][-2]["period"]
        items.append({"metric": "mom", "text": c.t("x_mom", p=L(pm), pc=spct(cur["dpct"]))})
    items.append({"metric": "ytd", "text": c.t("x_ytd", y=t["ytd_year"], n=t["ytd_months"], h=_g(t["ytd_hours"]), w=_g(t["ytd_weighted"]))})
    if len(a["avail"]) > 1:
        items.append({"metric": "peak", "text": c.t("x_peak", pm=L(t["peak"]), ph=_g(t["peak_hours"]), lm=L(t["low"]), lh=_g(t["low_hours"]))})
    items.append({"metric": "conc", "text": c.t("x_conc", k=t["concentration_n"], c=pct(t["concentration_pct"]))})
    if t["night_share"] is not None:
        items.append({"metric": "night", "text": c.t("x_night", m=L(cur["period"]), s=pct(t["night_share"]))})
    if t["missing"]:
        items.append({"metric": "missing", "text": c.t("x_missing", m="، ".join(L(p) for p in t["missing"]))})
    if t["empty_rows"]:
        items.append({"metric": "empty", "text": c.t("x_empty", n=t["empty_rows"])})
    if a["high"]:
        items.append({"metric": "high", "text": c.t("x_high", n=len(a["high"]), f=f"{th['high_month_factor']:g}")})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = [{"label": c.t("k_hours"), "value": _g(cur["hours"]), "sub": f"{L(cur['period'])} · {c.t('hours')}"}, {"label": c.t("k_weighted"), "value": _g(cur["weighted"]), "sub": ""},
                {"label": c.t("k_day"), "value": _g(cur["day_hours"]), "sub": c.t("hours")}, {"label": c.t("k_night"), "value": _g(cur["night_hours"]), "sub": c.t("hours")},
                {"label": c.t("k_active"), "value": str(cur["active"]), "sub": f"/ {cur['listed']}"}, {"label": c.t("k_avg"), "value": _g(cur["avg_per_active"]), "sub": c.t("hours")},
                {"label": c.t("k_meals"), "value": f"{cur['meals']:,.0f}", "sub": ""}, {"label": c.t("k_missions"), "value": f"{cur['mission_day'] + cur['mission_night']:,.0f}", "sub": ""},
                {"label": c.t("k_ytd", y=t["ytd_year"]), "value": _g(t["ytd_hours"]), "sub": f"{t['ytd_months']} · {c.t('hours')}"}, {"label": c.t("k_conc", n=t["concentration_n"]), "value": pct(t["concentration_pct"]), "sub": ""}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights.append({"severity": "info", "text": c.t("i_basis", d=f"{factors[0]:g}", n=f"{factors[1]:g}") if factors else c.t("i_basis_nofac")})
    sec.insights.append({"severity": "info", "text": c.t("i_period")})
    if focus:
        sec.insights.append({"severity": "info", "text": c.t("i_focus", m=L(focus))})
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    rm.sections.append(sec)

    sec = ReportSection(c.t("s_monthly"), "monthly")
    av = a["avail"]
    sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_month"), "x": [S(m["period"]) for m in av], "series": [
        {"name": c.t("c_day"), "values": [float(m["day_hours"]) for m in av]}, {"name": c.t("c_night"), "values": [float(m["night_hours"]) for m in av]}]})
    rows = []
    for m in reversed(a["months"]):
        if not m["available"]:
            rows.append({"p": L(m["period"]), "note": c.t("not_avail")})
            continue
        rows.append({"p": L(m["period"]), "h": m["hours"], "d": m["day_hours"], "n": m["night_hours"], "w": m["weighted"], "dw": m.get("d"), "dp": m.get("dpct"), "ls": m["listed"], "en": m["entries"], "ac": m["active"],
                     "ml": m["meals"], "md": m["mission_day"], "mn": m["mission_night"], "ns": m["night_share"], "note": c.t("large") if m["large"] else ""})
    sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [
        col("p", c.t("c_period")), col("h", c.t("c_hours"), "num"), col("d", c.t("c_day"), "num"), col("n", c.t("c_night"), "num"), col("w", c.t("c_weighted"), "num"), col("dw", c.t("c_d"), "snum"), col("dp", c.t("c_dpct"), "spct"),
        col("ls", c.t("c_listed"), "int"), col("en", c.t("c_entries"), "int"), col("ac", c.t("c_active"), "int"), col("ml", c.t("c_meals"), "int"), col("md", c.t("c_mday"), "int"), col("mn", c.t("c_mnight"), "int"),
        col("ns", c.t("c_nightsh"), "pct"), col("note", c.t("c_note"))], "rows": rows, "pdf_rows": 30})
    rm.sections.append(sec)

    sec = ReportSection(c.t("s_employees"), "employees")
    es = a["employees"]
    top = [e for e in es if e["hours"]][: int(th["top_n"])]
    if top:
        sec.charts.append({"type": "bar", "horizontal": True, "stacked": True, "title": c.t("ch_top"), "x": [who(e) for e in top], "series": [
            {"name": c.t("c_day"), "values": [float(e["day_hours"]) for e in top]}, {"name": c.t("c_night"), "values": [float(e["night_hours"]) for e in top]}]})
    ep = [m["period"] for m in av]
    if len(ep) > 1 and es:
        sec.charts.append({"type": "heatmap", "drill_rows": "employee", "title": c.t("ch_heat"), "rows": [who(e) for e in es[:25]], "cols": [S(p) for p in ep],
                           "values": [[float(e["by_month"].get(p, 0)) or None for p in ep] for e in es[:25]]})
    sec.tables.append({"key": "employees", "title": c.t("t_emp"), "columns": [col("code", c.t("c_code"))] + ([col("name", c.t("c_name"))] if admin else []) + [
        col("n", c.t("c_months"), "int"), col("day", c.t("c_day"), "num"), col("night", c.t("c_night"), "num"), col("h", c.t("c_hours"), "num"), col("w", c.t("c_weighted"), "num"), col("avg", c.t("c_avg"), "num"),
        col("mx", c.t("c_max")), col("ml", c.t("c_meals"), "int"), col("ms", c.t("c_missions"), "int"), col("sh", c.t("c_share"), "pct"), col("cum", c.t("c_cum"), "pct")],
        "rows": [{"code": e["code"], **({"name": e["name"] or "—"} if admin else {}), "n": e["n"], "day": e["day_hours"], "night": e["night_hours"], "h": e["hours"], "w": e["weighted"], "avg": e["avg_month"],
                  "mx": f"{S(e['max_month'][0])}: {e['max_month'][1]:,.1f}" if e["max_month"] else "—", "ml": e["meals"], "ms": e["missions"], "sh": e["share"], "cum": e["cum"]} for e in es], "pdf_rows": 40})
    if a["high"]:
        sec.tables.append({"key": "high", "title": c.t("t_high"), "columns": [col("e", c.t("c_code") if not admin else c.t("c_name")), col("p", c.t("c_period")), col("h", c.t("c_hours"), "num"), col("avg", c.t("c_avg"), "num"), col("f", c.t("c_factor"), "num")],
                           "rows": [{"e": who(x), "p": L(x["period"]), "h": x["hours"], "avg": x["avg"], "f": x["factor"]} for x in a["high"][:30]], "pdf_rows": 25})
    rm.sections.append(sec)

    sec = ReportSection(c.t("s_annual"), "annual")
    sec.tables.append({"key": "years", "title": c.t("t_years"), "columns": [col("y", c.t("c_year")), col("n", c.t("c_mcount"), "int"), col("day", c.t("c_day"), "num"), col("night", c.t("c_night"), "num"), col("h", c.t("c_hours"), "num"),
                                                                            col("w", c.t("c_weighted"), "num"), col("avg", c.t("c_avg"), "num"), col("ml", c.t("c_meals"), "int"), col("ms", c.t("c_missions"), "int")],
                       "rows": [{"y": y["year"], "n": y["months"], "day": y["day_hours"], "night": y["night_hours"], "h": y["hours"], "w": y["weighted"], "avg": y["avg_month"], "ml": y["meals"], "ms": y["missions"]} for y in a["years"]]})
    rm.sections.append(sec)

    fld = lambda f: c.s.get("fld_" + f, f)
    emp_name = {e["code"]: e["name"] for e in es}
    label_of = lambda x: (f"{emp_name.get(x['key']) or x['key']}" if admin else x["key"])
    rm.sections.append(versions_section(c, data["versions"], data["changes"], label_of, fld, L))
    extra = []
    ctrl = [x for s in data["summaries"][-1:] for x in s.get("controls", [])]
    if ctrl:
        extra.append({"key": "controls", "title": c.t("t_controls"), "note": c.t("ctl_note"), "columns": [col("f", c.t("c_field")), col("s", c.t("c_stated"), "num"), col("c", c.t("c_computed"), "num"), col("d", c.t("c_diff"), "snum")],
                      "rows": [{"f": fld(x["field"]), "s": x["stated"], "c": x["computed"], "d": x["diff"]} for x in ctrl]})
    rm.sections.append(quality_section(c, merged_issues(data["summaries"]), th, th_origin, [c.t("na_money"), c.t("na_attendance"), c.t("na_dept")], extra, [c.t("n_personal")]))
    return rm
