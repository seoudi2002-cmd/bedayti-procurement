"""ReportModel for rent analytics. Sentences come from computed numbers only; what the files do not support is stated as «not available»."""
from datetime import datetime, timezone

from app.core.analysis.opreport import C as BaseC, merged_issues, quality_section, versions_section
from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "تحليل إيجارات الفروع والمركز الرئيسي", "s_summary": "الملخص التنفيذي", "s_monthly": "الإيجار الشهري المسجَّل", "s_gov": "حسب المحافظة", "s_contracts": "حسب الفرع (العقد)",
        "s_changes": "الزيادات والتغييرات في قيمة الإيجار", "s_expiry": "انتهاء العقود", "egp": "ج.م", "unalloc": "Unallocated / يحتاج مراجعة", "hq": "المركز الرئيسي", "filtered": "عرض مفلتر",
        "asof": "حتى", "k_total": "إيجار الشهر المسجَّل", "k_year": "إجمالي المتاح من آخر 12 شهرًا ({n})", "k_contracts": "عقود لها قيمة في الشهر", "k_avg": "متوسط الإيجار للعقد", "k_hq": "المركز الرئيسي",
        "k_branches": "الفروع", "k_adv": "إجمالي المقدم المذكور", "k_dep": "إجمالي التأمين المذكور", "k_exp": "عقود تنتهي خلال {n} شهر", "k_steps": "تغيّرات في قيمة الإيجار", "k_up": "متوسط الزيادة العادية",
        "c_period": "الشهر", "c_total": "الإيجار المسجَّل", "c_d": "التغير", "c_dpct": "التغير %", "c_n": "عقود بقيمة", "c_nopay": "بلا سداد مسجَّل", "c_note": "ملاحظة", "c_gov": "المحافظة",
        "c_contracts": "العقود", "c_last": "آخر شهر", "c_prev": "الشهر السابق", "c_share": "النسبة %", "c_year": "آخر 12 شهرًا", "c_name": "الفرع / العقد", "c_start": "بداية العقد", "c_end": "نهاية العقد",
        "c_rent": "قيمة الإيجار بالعقد", "c_cur": "آخر قيمة مسجَّلة", "c_first": "أول قيمة مسجَّلة", "c_steps": "تغيّرات", "c_status": "الحالة", "c_adv": "المقدم", "c_dep": "التأمين", "c_landlord": "المالك",
        "c_old": "القيمة السابقة", "c_new": "القيمة الجديدة", "c_pct": "النسبة %", "c_events": "عدد التغيّرات", "c_avgpct": "متوسط النسبة %", "c_maxpct": "أكبر نسبة %", "c_blank": "أشهر بلا سداد",
        "c_recorded": "أشهر مسجَّلة", "c_ctrl": "إجمالي فرعي في الملف", "c_stated": "المذكور في الملف", "c_computed": "المحسوب", "c_matched": "مطابق", "c_mism": "غير مطابق", "c_periods": "أشهر",
        "t_months": "الإيجار المسجَّل شهريًا", "t_gov": "المحافظات (آخر شهر)", "t_matrix": "المحافظة × الشهر", "t_contracts": "العقود", "t_steps_m": "التغيّرات حسب الشهر", "t_steps_d": "توزيع نسب الزيادة العادية",
        "t_steps": "أحدث التغيّرات في قيمة الإيجار", "t_expiring": "عقود تنتهي قريبًا", "t_expired": "عقود انتهت ولها قيمة في آخر شهر", "t_expmonths": "عدد العقود المنتهية حسب الشهر", "t_periodic": "عقود بسداد دوري/غير منتظم (حسب الملف)",
        "t_noval": "عقود سارية بلا قيمة في آخر شهر", "t_controls": "مطابقة الإجماليات الفرعية في الملف", "ch_month": "الإيجار المسجَّل شهريًا", "ch_gov": "الإيجار حسب المحافظة (آخر شهر)", "ch_heat": "خريطة حرارية: المحافظة × الشهر",
        "st_active": "ساري", "st_ending": "ينتهي قريبًا", "st_expired": "منتهٍ", "st_unknown_end": "نهاية غير مقروءة", "partial": "—", "large": "تغير كبير", "not_avail": "لا توجد بيانات لهذا الشهر في الملف", "after_gap": "بعد شهر/أشهر بلا بيانات",
        "x_gapnote": " (مقارنة بآخر شهر متاح قبل فجوة في البيانات)", "x_missing": "أشهر بلا بيانات في الملف: {m}؛ لا تُقدَّر ولا تُحتسب صفرًا.",
        "x_partial": "أشهر ببيانات جزئية (لعدد قليل من العقود فقط): {m}؛ تظهر في الجدول ولا تدخل في المقارنات ولا في الإجماليات المعروضة.", "partial_note": "بيانات جزئية: لا تدخل في المقارنات",
        "x_total": "الإيجار المسجَّل في {m}: {v} ج.م على {n} عقد بقيمة (متوسط {a} ج.م).", "x_mom": "التغير عن {p}: {d} ج.م ({pc}).", "x_yoy": "مقارنة بنفس الشهر قبل سنة ({y}): {pc}.",
        "x_year": "إجمالي الأشهر المتاحة ضمن آخر 12 شهرًا ({n} شهرًا): {v} ج.م.", "x_gov": "أعلى محافظة: «{g}» ({v} ج.م، {s}).", "x_hq": "المركز الرئيسي {h} ج.م، الفروع {b} ج.م.",
        "x_steps": "{n} تغيّر في قيمة الإيجار، متوسط الزيادة العادية {a}.", "x_exp": "{n} عقد ينتهي خلال {w} أشهر، و{m} خلال {x} شهرًا.", "x_expired": "{n} عقد انتهى تاريخه وما زال له إيجار مسجَّل في آخر شهر.",
        "x_periodic": "{n} عقد بسداد دوري/غير منتظم: تظهر قيمه في أشهر السداد فقط ولا يُقسَّم الإيجار على أشهر لم يُسجَّل فيها شيء.",
        "x_unres": "{n} عقد بلا دليل صريح على المحافظة (Unallocated): لا يُوزَّع بالتخمين.", "x_noval": "{n} عقد ساري ليس له قيمة مسجَّلة في آخر شهر.",
        "i_basis": "المقياس = قيمة الإيجار الشهرية كما كُتبت في خانة الشهر. «_____» تعني عدم تسجيل سداد وليست صفرًا؛ ولا يُقدَّر أي رقم غير مذكور.",
        "i_gov": "المحافظة تؤخذ من ورقة المحافظة التي يجمع إجماليها الفرعي هذا العقد بمعادلة صريحة، وإلا من اسم الفرع إن ذكرها بين قوسين؛ غير ذلك Unallocated.",
        "i_filtered": "العرض مفلتر؛ المقارنات والنسب على المحافظات/العقود المختارة فقط.", "i_focus": "لقطة حتى {m}: أي بيانات لاحقة لهذا الشهر غير مدخلة هنا.",
        "na_actual": "المدفوع فعليًا وتواريخ الصرف: لا يوجد سجل مدفوعات", "na_reason": "سبب تغيّر الإيجار (زيادة سنوية أم تعديل عقد): غير مذكور في الملف", "na_area": "مساحة الفرع وسعر المتر: غير موجودة",
        "na_before": "قيم قبل يناير 2023: لا توجد", "n_personal": "أسماء الملّاك بيانات شخصية: تظهر للمدير فقط.",
        "f_gov": "المحافظة", "f_contract": "العقد", "fld_rent": "الإيجار", "fld_governorate": "المحافظة", "fld_start": "بداية العقد", "fld_end": "نهاية العقد", "fld_advance": "المقدم", "fld_deposit": "التأمين",
        "fld_contract_rent": "القيمة بالعقد", "fld_no_payment": "بلا سداد", "fld_scope": "النطاق", "fld_start_raw": "بداية (نص)", "fld_end_raw": "نهاية (نص)", "fld_current_rent_stated": "القيمة الحالية المذكورة",
        "ctl_note": "الإجمالي الفرعي المذكور في ورقة المحافظة مقابل مجموع عقودها كما حُسبت هنا؛ الفروق تُعرض ولا تُصحَّح.",
    },
    "en": {
        "title": "Branch and Head Office rent analysis", "s_summary": "Executive summary", "s_monthly": "Recorded rent by month", "s_gov": "By governorate", "s_contracts": "By branch (contract)",
        "s_changes": "Increases and changes in the rent value", "s_expiry": "Contract expiry", "egp": "EGP", "unalloc": "Unallocated / needs review", "hq": "Head Office", "filtered": "Filtered view",
        "asof": "up to", "k_total": "Recorded rent for the month", "k_year": "Available months of the last 12 ({n})", "k_contracts": "Contracts with a value this month", "k_avg": "Average rent per contract", "k_hq": "Head Office",
        "k_branches": "Branches", "k_adv": "Advance stated (total)", "k_dep": "Deposit stated (total)", "k_exp": "Contracts ending within {n} months", "k_steps": "Changes in rent value", "k_up": "Average regular increase",
        "c_period": "Month", "c_total": "Recorded rent", "c_d": "Change", "c_dpct": "Change %", "c_n": "Contracts with a value", "c_nopay": "No payment recorded", "c_note": "Note", "c_gov": "Governorate",
        "c_contracts": "Contracts", "c_last": "Last month", "c_prev": "Previous month", "c_share": "Share %", "c_year": "Last 12 months", "c_name": "Branch / contract", "c_start": "Start", "c_end": "End",
        "c_rent": "Rent per contract", "c_cur": "Last recorded value", "c_first": "First recorded value", "c_steps": "Changes", "c_status": "Status", "c_adv": "Advance", "c_dep": "Deposit", "c_landlord": "Landlord",
        "c_old": "Previous value", "c_new": "New value", "c_pct": "%", "c_events": "Changes", "c_avgpct": "Average %", "c_maxpct": "Largest %", "c_blank": "Months without payment",
        "c_recorded": "Recorded months", "c_ctrl": "Sub-total in the file", "c_stated": "Stated in the file", "c_computed": "Computed", "c_matched": "Matching", "c_mism": "Not matching", "c_periods": "Months",
        "t_months": "Recorded rent by month", "t_gov": "Governorates (last month)", "t_matrix": "Governorate × month", "t_contracts": "Contracts", "t_steps_m": "Changes by month", "t_steps_d": "Distribution of regular increase rates",
        "t_steps": "Latest changes in rent value", "t_expiring": "Contracts ending soon", "t_expired": "Contracts past their end date with a value in the last month", "t_expmonths": "Contracts ending, by month", "t_periodic": "Periodic / irregular payers (per the file)",
        "t_noval": "Active contracts with no value in the last month", "t_controls": "Reconciling the file's own sub-totals", "ch_month": "Recorded rent by month", "ch_gov": "Rent by governorate (last month)", "ch_heat": "Heatmap: governorate × month",
        "st_active": "Active", "st_ending": "Ending soon", "st_expired": "Expired", "st_unknown_end": "End date unreadable", "partial": "—", "large": "Large change", "not_avail": "No data for this month in the file", "after_gap": "After month(s) with no data",
        "x_gapnote": " (compared with the last available month before a gap in the data)", "x_missing": "Months with no data in the file: {m}; not estimated and not counted as zero.",
        "x_partial": "Months with partial data (only a few contracts have an entry): {m}; shown in the table but left out of comparisons and of the totals shown.", "partial_note": "Partial data: not compared",
        "x_total": "Recorded rent in {m}: {v} EGP across {n} contracts with a value (average {a} EGP).", "x_mom": "Change vs {p}: {d} EGP ({pc}).", "x_yoy": "Compared with the same month a year earlier ({y}): {pc}.",
        "x_year": "Total of the available months within the last 12 months ({n} months): {v} EGP.", "x_gov": "Largest governorate: «{g}» ({v} EGP, {s}).", "x_hq": "Head Office {h} EGP, branches {b} EGP.",
        "x_steps": "{n} changes in rent value; average regular increase {a}.", "x_exp": "{n} contracts end within {w} months, {m} within {x} months.", "x_expired": "{n} contracts are past their end date yet still have rent recorded in the last month.",
        "x_periodic": "{n} contracts pay periodically / irregularly: their values show only in the months paid; rent is never spread over months with nothing recorded.",
        "x_unres": "{n} contracts have no explicit governorate evidence (Unallocated): not allocated by guessing.", "x_noval": "{n} active contracts have no recorded value in the last month.",
        "i_basis": "Measure = the monthly rent as written in the month cell. «_____» means no payment recorded, not zero; no unstated number is estimated.",
        "i_gov": "The governorate comes from the governorate sheet whose sub-total adds the contract up with an explicit formula, else from the branch name when it states one in brackets; otherwise Unallocated.",
        "i_filtered": "Filtered view; comparisons and shares cover the selected governorates / contracts only.", "i_focus": "Snapshot up to {m}: later data is not included here.",
        "na_actual": "What was actually paid and payment dates: there is no payments record", "na_reason": "Why the rent changed (annual increase or an amendment): not stated in the file", "na_area": "Branch area and price per metre: not present",
        "na_before": "Values before January 2023: none", "n_personal": "Landlord names are personal data: shown to admins only.",
        "f_gov": "Governorate", "f_contract": "Contract", "fld_rent": "Rent", "fld_governorate": "Governorate", "fld_start": "Start", "fld_end": "End", "fld_advance": "Advance", "fld_deposit": "Deposit",
        "fld_contract_rent": "Contract rent", "fld_no_payment": "No payment", "fld_scope": "Scope", "fld_start_raw": "Start (text)", "fld_end_raw": "End (text)", "fld_current_rent_stated": "Current rent stated",
        "ctl_note": "The sub-total stated in a governorate sheet against the sum of its contracts as computed here; differences are shown, not corrected.",
    },
}


class C(BaseC):
    def __init__(self, lang):
        super().__init__(lang, T)


def _m(lang, p, short=False):
    return period_label(lang, (int(p[:4]), int(p[5:7])), short)


def _ranges(lang, ps: list[str]) -> str:
    """Consecutive months as 'first – last' groups."""
    out, run = [], [ps[0]]
    for p in ps[1:]:
        y, m = int(run[-1][:4]), int(run[-1][5:7])
        nxt = f"{y + (m == 12)}-{m % 12 + 1:02d}"
        if p == nxt:
            run.append(p)
        else:
            out.append(run)
            run = [p]
    out.append(run)
    return "، ".join(_m(lang, g[0]) if len(g) == 1 else f"{_m(lang, g[0])} – {_m(lang, g[-1])}" for g in out)


def build_report(a: dict, data: dict, th: dict, th_origin: dict, lang: str, filters: dict, dims: list[dict], admin: bool, focus: str | None) -> ReportModel:
    c = C(lang)
    t = a["totals"]
    months = a["months"]
    L = lambda p: _m(lang, p)
    gname = lambda g: c.t("hq") if g == "المركز الرئيسي" else (g if g else c.t("unalloc"))
    rm = ReportModel(title=c.t("title"), period_label=f"{L(a['periods'][0])} – {L(a['periods'][-1])}", sections=[], lang=lang)
    files = [v["file"] for v in data["versions"]]
    rm.subtitle = " · ".join(files[-3:]) + (" · " + c.t("filtered") if a["filtered"] else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(files[-3:]), "file_hash": "", "filters": {"active": filters, "options": {}, "dimensions": dims}}
    egp = c.t("egp")

    # ---------------------------------------------------------------- summary
    items = [{"metric": "total", "text": c.t("x_total", m=L(t["last"]), v=money2(t["total_last"]), n=t["with_value_last"], a=money2(t["avg_per_contract"]) if t["avg_per_contract"] else "—")}]
    if t["d"] is not None:
        items.append({"metric": "mom", "text": c.t("x_mom", p=L(t["prev"]), d=smoney(t["d"]), pc=spct(t["dpct"])) + (c.t("x_gapnote") if t["gap_before_last"] else "")})
    if t["yoy_pct"] is not None:
        items.append({"metric": "yoy", "text": c.t("x_yoy", y=L(t["yoy"]), pc=spct(t["yoy_pct"]))})
    items.append({"metric": "year", "text": c.t("x_year", n=t["year_months"], v=money2(t["year_total"]))})
    if t["missing"]:
        items.append({"metric": "missing", "text": c.t("x_missing", m=_ranges(lang, t["missing"]))})
    if t["partial_months"]:
        items.append({"metric": "partial", "text": c.t("x_partial", m=_ranges(lang, t["partial_months"]))})
    g0 = next((g for g in a["governorates"] if g["last"]), None)
    if g0:
        items.append({"metric": "gov", "text": c.t("x_gov", g=gname(g0["name"]), v=money2(g0["last"]), s=pct(g0["share"]))})
    if t["hq_last"] or t["branches_last"]:
        items.append({"metric": "hq", "text": c.t("x_hq", h=money2(t["hq_last"]), b=money2(t["branches_last"]))})
    if t["step_events"]:
        items.append({"metric": "steps", "text": c.t("x_steps", n=t["step_events"], a=pct(t["avg_up_pct"]))})
    items.append({"metric": "exp", "text": c.t("x_exp", n=t["expiring"], w=t["expiring_window"], m=t["expiring_long"], x=t["expiring_long_window"])})
    if t["expired_with_value"]:
        items.append({"metric": "expired", "text": c.t("x_expired", n=t["expired_with_value"])})
    if t["periodic"]:
        items.append({"metric": "periodic", "text": c.t("x_periodic", n=t["periodic"])})
    if t["unresolved"]:
        items.append({"metric": "unres", "text": c.t("x_unres", n=t["unresolved"])})
    if a["active_no_value"]:
        items.append({"metric": "noval", "text": c.t("x_noval", n=len(a["active_no_value"]))})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = [{"label": c.t("k_total"), "value": money2(t["total_last"]), "sub": f"{L(t['last'])} · {egp}"}, {"label": c.t("k_year", n=t["year_months"]), "value": money2(t["year_total"]), "sub": egp},
                {"label": c.t("k_contracts"), "value": str(t["with_value_last"]), "sub": f"/ {t['contracts']}"}, {"label": c.t("k_avg"), "value": money2(t["avg_per_contract"]) if t["avg_per_contract"] else "—", "sub": egp},
                {"label": c.t("k_hq"), "value": money2(t["hq_last"]), "sub": egp}, {"label": c.t("k_branches"), "value": money2(t["branches_last"]), "sub": egp},
                {"label": c.t("k_adv"), "value": money2(t["advance_total"]), "sub": f"{t['advance_n']} · {egp}"}, {"label": c.t("k_dep"), "value": money2(t["deposit_total"]), "sub": f"{t['deposit_n']} · {egp}"},
                {"label": c.t("k_exp", n=t["expiring_window"]), "value": str(t["expiring"]), "sub": ""}, {"label": c.t("k_steps"), "value": str(t["step_events"]), "sub": ""}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights += [{"severity": "info", "text": c.t("i_basis")}, {"severity": "info", "text": c.t("i_gov")}]
    if focus:
        sec.insights.append({"severity": "info", "text": c.t("i_focus", m=L(focus))})
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- monthly
    sec = ReportSection(c.t("s_monthly"), "monthly")
    show = a["avail"][-36:]
    sec.charts.append({"type": "bar", "title": c.t("ch_month"), "x": [_m(lang, m["period"], True) for m in show], "series": [{"name": c.t("c_total"), "values": [float(m["total"]) for m in show]}]})
    sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [col("p", c.t("c_period")), col("v", c.t("c_total"), "money"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct"),
                                                                              col("n", c.t("c_n"), "int"), col("np", c.t("c_nopay"), "int"), col("note", c.t("c_note"))],
                       "rows": [({"p": L(m["period"]), "note": c.t("not_avail")} if not m["available"] else
                                 {"p": L(m["period"]), "v": m["total"], "d": m.get("d"), "dp": m.get("dpct"), "n": m["n"], "np": m["nopay"],
                                  "note": c.t("partial_note") if m.get("partial") else (c.t("large") if m["large"] else (c.t("after_gap") if m.get("gap_before") else ""))}) for m in reversed(months)], "pdf_rows": 40})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- governorates
    sec = ReportSection(c.t("s_gov"), "governorates")
    gs = [g for g in a["governorates"] if g["last"] or g["contracts"]]
    top = [g for g in gs if g["last"]][: int(th["top_n"]) + 6]
    if top:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_gov"), "x": [gname(g["name"]) for g in top], "series": [{"name": c.t("c_last"), "values": [float(g["last"]) for g in top]}]})
    mp = a["matrix_periods"]
    if len(mp) > 1 and gs:
        sec.charts.append({"type": "heatmap", "drill_rows": "governorate", "title": c.t("ch_heat"), "rows": [gname(g["name"]) for g in gs[:20]], "cols": [_m(lang, p, True) for p in mp],
                           "values": [[float(g["by_month"].get(p, 0)) or None for p in mp] for g in gs[:20]]})
    sec.tables.append({"key": "governorates", "title": c.t("t_gov"), "columns": [col("g", c.t("c_gov")), col("n", c.t("c_contracts"), "int"), col("last", c.t("c_last"), "money"), col("prev", c.t("c_prev"), "money"),
                                                                                col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct"), col("sh", c.t("c_share"), "pct"), col("yr", c.t("c_year"), "money")],
                       "rows": [{"g": gname(g["name"]), "n": g["contracts"], "last": g["last"], "prev": g["prev"], "d": g["d"], "dp": g["dpct"], "sh": g["share"], "yr": g["year"]} for g in gs]})
    sec.tables.append({"key": "gov_matrix", "title": c.t("t_matrix"), "columns": [col("g", c.t("c_gov"))] + [col(f"p{i}", _m(lang, p, True), "money") for i, p in enumerate(mp)],
                       "rows": [{"g": gname(g["name"]), **{f"p{i}": g["by_month"].get(p) for i, p in enumerate(mp)}} for g in gs], "pdf_rows": 30})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- contracts
    sec = ReportSection(c.t("s_contracts"), "contracts")
    cols = [col("name", c.t("c_name")), col("g", c.t("c_gov")), col("start", c.t("c_start")), col("end", c.t("c_end")), col("rent", c.t("c_rent"), "money"), col("first", c.t("c_first"), "money"),
            col("last", c.t("c_cur"), "money"), col("steps", c.t("c_steps"), "int"), col("st", c.t("c_status")), col("adv", c.t("c_adv"), "money"), col("dep", c.t("c_dep"), "money")]
    if admin:
        cols.append(col("ll", c.t("c_landlord")))
    sec.tables.append({"key": "contracts", "title": c.t("t_contracts"), "columns": cols, "pdf_rows": 40,
                       "rows": [{"name": r["name"], "g": gname(r["governorate"]), "start": r["start"].isoformat() if r["start"] else (r["start_raw"] or "—"), "end": r["end"].isoformat() if r["end"] else "—",
                                 "rent": r["contract_rent"], "first": r["first"], "last": r["last"], "steps": r["steps"], "st": c.t("st_" + r["status"]), "adv": r["advance"], "dep": r["deposit"],
                                 **({"ll": r["landlord"] or "—"} if admin else {})} for r in a["rows"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- changes
    sec = ReportSection(c.t("s_changes"), "steps")
    sec.tables.append({"key": "steps_by_month", "title": c.t("t_steps_m"), "columns": [col("p", c.t("c_period")), col("n", c.t("c_events"), "int"), col("avg", c.t("c_avgpct"), "spct"), col("max", c.t("c_maxpct"), "spct")],
                       "rows": [{"p": L(x["period"]), "n": x["n"], "avg": x["avg_pct"], "max": x["max_pct"]} for x in a["step_by_month"]], "pdf_rows": 30})
    sec.tables.append({"key": "steps_dist", "title": c.t("t_steps_d"), "columns": [col("pct", c.t("c_pct"), "spct"), col("n", c.t("c_events"), "int")], "rows": [{"pct": x["pct"], "n": x["n"]} for x in a["step_dist"]]})
    sec.tables.append({"key": "steps", "title": c.t("t_steps"), "columns": [col("name", c.t("c_name")), col("g", c.t("c_gov")), col("p", c.t("c_period")), col("old", c.t("c_old"), "money"), col("new", c.t("c_new"), "money"),
                                                                           col("pct", c.t("c_pct"), "spct"), col("note", c.t("c_note"))],
                       "rows": [{"name": s["name"], "g": gname(s["governorate"]), "p": L(s["period"]), "old": s["old"], "new": s["new"], "pct": s["pct"], "note": c.t("large") if s["large"] else ""} for s in a["steps"][:80]], "pdf_rows": 40})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- expiry
    sec = ReportSection(c.t("s_expiry"), "expiry")
    ecols = [col("name", c.t("c_name")), col("g", c.t("c_gov")), col("end", c.t("c_end")), col("last", c.t("c_cur"), "money")]
    erow = lambda r: {"name": r["name"], "g": gname(r["governorate"]), "end": r["end"].isoformat() if r["end"] else "—", "last": r["last"]}
    sec.tables.append({"key": "expiring", "title": c.t("t_expiring"), "columns": ecols, "rows": [erow(r) for r in a["expiring"]], "pdf_rows": 30})
    if a["expired_with_value"]:
        sec.tables.append({"key": "expired", "title": c.t("t_expired"), "columns": ecols, "rows": [erow(r) for r in a["expired_with_value"]]})
    sec.tables.append({"key": "expiry_months", "title": c.t("t_expmonths"), "columns": [col("p", c.t("c_period")), col("n", c.t("c_contracts"), "int")],
                       "rows": [{"p": L(p), "n": n} for p, n in a["expiry_months"].items()], "pdf_rows": 30})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- versions + quality
    fld = lambda f: c.s.get("fld_" + f, f)
    rm.sections.append(versions_section(c, data["versions"], data["changes"], lambda x: x["label"], fld, L))
    extra = []
    ctrl = [x for s in data["summaries"][-1:] for x in s.get("controls", [])]
    if ctrl:
        extra.append({"key": "controls", "title": c.t("t_controls"), "note": c.t("ctl_note"), "columns": [col("s", c.t("c_gov")), col("pe", c.t("c_periods"), "int"), col("ok", c.t("c_matched"), "int"), col("bad", c.t("c_mism"), "int"),
                                                                                                         col("ex", c.t("c_note"))],
                      "rows": [{"s": gname(x["sheet"]), "pe": x["periods"], "ok": x["matched"], "bad": x["mismatched"],
                                "ex": " | ".join(f"{L(e['period'])}: {money(e['stated'])} ≠ {money(e['computed'])}" for e in x["examples"][:2])} for x in ctrl]})
    if a["periodic"]:
        extra.append({"key": "periodic", "title": c.t("t_periodic"), "columns": [col("name", c.t("c_name")), col("g", c.t("c_gov")), col("b", c.t("c_blank"), "int"), col("r", c.t("c_recorded"), "int")],
                      "rows": [{"name": r["name"], "g": gname(r["governorate"]), "b": r["blank_months"], "r": r["recorded_months"]} for r in a["periodic"]], "pdf_rows": 25})
    if a["active_no_value"]:
        extra.append({"key": "no_value", "title": c.t("t_noval"), "columns": [col("name", c.t("c_name")), col("g", c.t("c_gov")), col("end", c.t("c_end"))],
                      "rows": [{"name": r["name"], "g": gname(r["governorate"]), "end": r["end"].isoformat() if r["end"] else "—"} for r in a["active_no_value"]], "pdf_rows": 25})
    rm.sections.append(quality_section(c, merged_issues(data["summaries"]), th, th_origin, [c.t("na_actual"), c.t("na_reason"), c.t("na_area"), c.t("na_before")], extra, [c.t("n_personal")]))
    return rm
