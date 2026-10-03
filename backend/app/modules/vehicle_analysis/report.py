"""ReportModel for vehicle fleet analytics. Sentences come from computed numbers only; what the files do not support is stated as «not available»."""
from datetime import datetime, timezone

from app.core.analysis.opreport import C as BaseC, merged_issues, quality_section, versions_section
from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "تحليل أسطول السيارات (الصيانة والوقود والاستخدام)", "s_summary": "الملخص التنفيذي", "s_monthly": "التكلفة الشهرية", "s_categories": "بنود التكلفة", "s_vehicles": "حسب السيارة",
        "s_fuel": "الوقود والمسافة", "s_service": "مواعيد الصيانة (كارت الصيانة)", "s_claims": "مطالبات التأمين", "s_coverage": "تغطية البيانات وربط السيارات", "egp": "ج.م", "filtered": "عرض مفلتر",
        "k_total": "إجمالي التكلفة", "k_maint": "الصيانة", "k_fuel": "الوقود", "k_cur": "تكلفة آخر شهر", "k_vehicles": "سيارات لها تكلفة", "k_cpk": "تكلفة الكيلومتر", "k_due": "بنود صيانة مستحقة/قريبة", "k_claims": "مطالبات التأمين",
        "k_outliers": "شهور سيارات شاذة",
        "c_period": "الشهر", "c_vehicles": "سيارات", "c_active": "بتكلفة", "c_total": "الإجمالي", "c_maint": "الصيانة", "c_fuel": "الوقود", "c_qty": "كمية الوقود (مشتقة)", "c_km": "كم", "c_d": "التغير", "c_dpct": "التغير %",
        "c_note": "ملاحظة", "c_cat": "البند", "c_share": "النسبة %", "c_cum": "التراكمي %", "c_plate": "السيارة", "c_type": "النوع", "c_months": "أشهر بأرقام", "c_avg": "متوسط الشهر", "c_max": "أعلى شهر", "c_cpk": "تكلفة/كم",
        "c_kmm": "أشهر فيها مسافة", "c_cons": "كم/لتر", "c_median": "وسيط الشهر", "c_factor": "المضاعف", "c_sources": "المصادر", "c_price": "سعر اللتر في المعادلة", "c_derived": "الكمية المشتقة", "c_stated": "الكمية المذكورة (تقرير الاستخدام)",
        "c_statem": "كم (بيان الإصلاحات)", "c_usage": "كم (تقرير الاستخدام)", "c_daily": "مجموع الأيام", "c_odo": "فرق العداد", "c_item": "البند", "c_odometer": "العداد", "c_next": "الموعد القادم (كم)", "c_rem": "المتبقي (كم)", "c_state": "الحالة",
        "c_desc": "البيان", "c_orig": "أصل المبلغ", "c_ins": "تحمل التأمين", "c_co": "تحمل الشركة", "c_number": "الرقم", "c_plates": "كتابات اللوحة", "c_match": "أشهر تطابقت فيها المسافة", "c_stated2": "المذكور", "c_computed": "المحسوب", "c_diff": "الفرق",
        "c_rate": "المعدل المذكور",
        "t_months": "التكلفة الشهرية", "t_cats": "بنود التكلفة (كما كُتبت في الملف)", "t_vehicles": "السيارات", "t_outliers": "أشهر أعلى كثيرًا من وسيط السيارة نفسها", "t_prices": "سعر اللتر المكتوب في معادلة الكمية",
        "t_fuel": "الكمية المشتقة مقابل المذكورة والاستهلاك", "t_km": "مقارنة المسافة بين المصادر", "t_due": "بنود الصيانة (آخر كارت لكل سيارة)", "t_claims": "المطالبات", "t_cov": "التغطية: C تكلفة، U استخدام، S كارت صيانة",
        "t_cand": "كتابات لوحة قد تكون لسيارة واحدة (لم تُربط)", "t_ctl": "مطابقة إجمالي الشهر المذكور بمجموع السيارات", "t_half": "مطابقة إجمالي نصف العام لكل سيارة بمجموع الأشهر",
        "ch_month": "التكلفة الشهرية: صيانة ووقود", "ch_cat": "بنود التكلفة", "ch_veh": "أعلى السيارات تكلفة", "ch_heat": "خريطة حرارية: السيارة × الشهر",
        "partial": "شهر غير مكتمل غالبًا", "large": "تغير كبير", "st_overdue": "متأخر", "st_soon": "قريب", "st_ok": "سليم", "unalloc": "—",
        "x_total": "إجمالي التكلفة المذكورة {v} ج.م لـ {n} سيارة خلال {m} ({k} شهرًا): صيانة {mt} ج.م ووقود {f} ج.م.", "x_cur": "تكلفة {m}: {v} ج.م ({n} سيارة بتكلفة).",
        "x_partial": "{m} يبدو غير مكتمل (سيارات بتكلفة أقل كثيرًا من المعتاد)؛ لا يُقارن كشهر كامل.", "x_top": "أعلى سيارة تكلفة {p} ({v} ج.م، {s}).", "x_cat": "أعلى بند «{c}» ({v} ج.م، {s}).",
        "x_cpk": "تكلفة الكيلومتر {v} ج.م محسوبة على {k} كم من أشهر فيها مسافة فقط (لا تغطي كل السيارات).", "x_outliers": "{n} حالة سيارة-شهر أعلى من {f}× وسيط السيارة نفسها.",
        "x_due": "{n} بند صيانة مستحق أو خلال {k} كم حسب آخر كارت.", "x_claims": "مطالبات تأمين: أصل {o} ج.م، تحمّلت الشركة {c} ج.م.", "x_maint_basis": "{n} صف بلا إجمالي صيانة مذكور وله بنود تكلفة: اعتُمد مجموع بنوده المذكورة للصيانة (والإجمالي العام كما كُتب).", "x_cand": "{n} كتابة لوحة قد تخص سيارة واحدة ولم تُربط تلقائيًا (راجع جدول الربط).",
        "i_basis": "الأرقام هي المذكورة في ملف الإصلاحات: إجمالي الصيانة وإجمالي الوقود والإجمالي العام كما كُتبت. الشهر الذي لا رقم لسيارة فيه ليس صفرًا.",
        "i_qty": "كمية الوقود في بيان الإصلاحات مشتقة (التكلفة ÷ سعر اللتر المكتوب في معادلتها) وليست مقيسة؛ لذا لا يُحسب منها معدل استهلاك. الاستهلاك يُحسب فقط من تقرير الاستخدام (المسافة والوقود المذكوران فيه).",
        "i_cpk": "تكلفة الكيلومتر تُحسب على الأشهر التي لها مسافة فقط؛ المسافة المتاحة جزئية.", "i_link": "اللوحات تُربط بالتطابق التام أو بمصدر أرقام فقط ذي رقم فريد أو بمرادف معتمد في الإعدادات؛ غير ذلك تبقى منفصلة.",
        "i_filtered": "العرض مفلتر على السيارات المختارة.", "i_focus": "لقطة حتى {m}.",
        "na_register": "سجل المركبات (سنة الصنع، الشاسيه، انتهاء الرخصة والتأمين): غير موجود فلا تنبيهات تجديد", "na_measured": "كمية الوقود المقيسة وسعر اللتر الفعلي: غير موجودة إلا ما ذُكر في تقرير الاستخدام", "na_driver": "تكلفة السائق وتشغيله: غير موجودة",
        "na_before": "بيانات قبل يناير 2026: غير موجودة", "n_personal": "أسماء السائقين والملاحظات التي تذكر أشخاصًا بيانات شخصية: تظهر للمدير فقط.", "f_vehicle": "السيارة", "ctl_note": "المذكور في الملف مقابل المحسوب هنا؛ الفروق تُعرض ولا تُصحَّح.",
        "fld_maint_total": "إجمالي الصيانة", "fld_fuel_cost": "تكلفة الوقود", "fld_fuel_qty": "كمية الوقود", "fld_grand_total": "الإجمالي العام", "fld_km": "المسافة", "fld_type": "النوع", "fld_note": "ملاحظة", "fld_odometer": "العداد",
        "fld_fuel_price_in_formula": "سعر اللتر", "fld_km_total": "المسافة", "fld_original": "أصل المبلغ", "fld_insurer_share": "تحمل التأمين", "fld_company_share": "تحمل الشركة",
    },
    "en": {
        "title": "Vehicle fleet analysis (maintenance, fuel and usage)", "s_summary": "Executive summary", "s_monthly": "Monthly cost", "s_categories": "Cost items", "s_vehicles": "By vehicle",
        "s_fuel": "Fuel and distance", "s_service": "Service due (maintenance card)", "s_claims": "Insurance claims", "s_coverage": "Data coverage and vehicle linking", "egp": "EGP", "filtered": "Filtered view",
        "k_total": "Total cost", "k_maint": "Maintenance", "k_fuel": "Fuel", "k_cur": "Last month's cost", "k_vehicles": "Vehicles with a cost", "k_cpk": "Cost per km", "k_due": "Service items due / soon", "k_claims": "Insurance claims",
        "k_outliers": "Outlier vehicle-months",
        "c_period": "Month", "c_vehicles": "Vehicles", "c_active": "With a cost", "c_total": "Total", "c_maint": "Maintenance", "c_fuel": "Fuel", "c_qty": "Fuel quantity (derived)", "c_km": "km", "c_d": "Change", "c_dpct": "Change %",
        "c_note": "Note", "c_cat": "Item", "c_share": "Share %", "c_cum": "Cumulative %", "c_plate": "Vehicle", "c_type": "Type", "c_months": "Months with figures", "c_avg": "Monthly average", "c_max": "Highest month", "c_cpk": "Cost/km",
        "c_kmm": "Months with a distance", "c_cons": "km/L", "c_median": "Median month", "c_factor": "Multiple", "c_sources": "Sources", "c_price": "Price per litre in the formula", "c_derived": "Derived quantity", "c_stated": "Stated quantity (usage report)",
        "c_statem": "km (repairs statement)", "c_usage": "km (usage report)", "c_daily": "Sum of days", "c_odo": "Odometer difference", "c_item": "Item", "c_odometer": "Odometer", "c_next": "Next due (km)", "c_rem": "Remaining (km)", "c_state": "State",
        "c_desc": "Description", "c_orig": "Original amount", "c_ins": "Insurer share", "c_co": "Company share", "c_number": "Number", "c_plates": "Plate spellings", "c_match": "Months the distance matched", "c_stated2": "Stated", "c_computed": "Computed", "c_diff": "Difference",
        "c_rate": "Stated rate",
        "t_months": "Monthly cost", "t_cats": "Cost items (as written in the file)", "t_vehicles": "Vehicles", "t_outliers": "Months far above the vehicle's own median", "t_prices": "Price per litre written in the quantity formula",
        "t_fuel": "Derived vs stated quantity and consumption", "t_km": "Distance compared across sources", "t_due": "Service items (latest card per vehicle)", "t_claims": "Claims", "t_cov": "Coverage: C cost, U usage, S maintenance card",
        "t_cand": "Plate spellings that may be one vehicle (not linked)", "t_ctl": "A month's stated total against the sum of its vehicles", "t_half": "The half-year total per vehicle against the sum of the months",
        "ch_month": "Monthly cost: maintenance and fuel", "ch_cat": "Cost items", "ch_veh": "Highest-cost vehicles", "ch_heat": "Heatmap: vehicle × month",
        "partial": "Probably incomplete month", "large": "Large change", "st_overdue": "Overdue", "st_soon": "Soon", "st_ok": "OK", "unalloc": "—",
        "x_total": "Total stated cost {v} EGP for {n} vehicles over {m} ({k} months): maintenance {mt} EGP and fuel {f} EGP.", "x_cur": "Cost of {m}: {v} EGP ({n} vehicles with a cost).",
        "x_partial": "{m} looks incomplete (far fewer vehicles with a cost than usual); do not compare it as a full month.", "x_top": "Highest-cost vehicle {p} ({v} EGP, {s}).", "x_cat": "Largest item «{c}» ({v} EGP, {s}).",
        "x_cpk": "Cost per km {v} EGP computed on {k} km from months that have a distance only (not every vehicle).", "x_outliers": "{n} vehicle-months are above {f}× the vehicle's own median.",
        "x_due": "{n} service items are due or within {k} km according to the latest card.", "x_claims": "Insurance claims: original {o} EGP, company bore {c} EGP.", "x_maint_basis": "{n} rows state no maintenance total but have cost items: the sum of their stated items is used for maintenance (the grand total is as written).", "x_cand": "{n} plate spellings may belong to one vehicle and were not linked automatically (see the linking table).",
        "i_basis": "Figures are those stated in the repairs file: maintenance total, fuel total and grand total as written. A month with no figure for a vehicle is not zero.",
        "i_qty": "The fuel quantity in the repairs statement is derived (cost ÷ the price per litre written in its formula), not measured, so no consumption rate is computed from it. Consumption is computed only from the usage report (its own distance and fuel).",
        "i_cpk": "Cost per km uses only months that have a distance; the distance available is partial.", "i_link": "Plates are linked only by an exact match, a digits-only source with a unique number, or an approved alias in the settings; otherwise they stay separate.",
        "i_filtered": "Filtered to the selected vehicles.", "i_focus": "Snapshot up to {m}.",
        "na_register": "Vehicle register (model year, chassis, licence and insurance expiry): not present, so no renewal alerts", "na_measured": "Measured fuel quantity and the actual price per litre: not present beyond what the usage report states", "na_driver": "Driver cost and operation: not present",
        "na_before": "Data before January 2026: not present", "n_personal": "Driver names and notes that mention people are personal data: shown to admins only.", "f_vehicle": "Vehicle", "ctl_note": "Stated in the file against computed here; differences are shown, not corrected.",
        "fld_maint_total": "Maintenance total", "fld_fuel_cost": "Fuel cost", "fld_fuel_qty": "Fuel quantity", "fld_grand_total": "Grand total", "fld_km": "Distance", "fld_type": "Type", "fld_note": "Note", "fld_odometer": "Odometer",
        "fld_fuel_price_in_formula": "Price per litre", "fld_km_total": "Distance", "fld_original": "Original amount", "fld_insurer_share": "Insurer share", "fld_company_share": "Company share",
    },
}


class C(BaseC):
    def __init__(self, lang):
        super().__init__(lang, T)


def _m(lang, p, short=False):
    return period_label(lang, (int(p[:4]), int(p[5:7])), short)


def build_report(a: dict, data: dict, th: dict, th_origin: dict, lang: str, filters: dict, dims: list[dict], admin: bool, focus: str | None) -> ReportModel:
    c = C(lang)
    t = a["totals"]
    L = lambda p: _m(lang, p)
    S = lambda p: _m(lang, p, True)
    egp = c.t("egp")
    files = [v["file"] for v in data["versions"]]
    per = a["periods"]
    rm = ReportModel(title=c.t("title"), period_label=f"{L(per[0])} – {L(per[-1])}", sections=[], lang=lang)
    rm.subtitle = " · ".join(files[-3:]) + (" · " + c.t("filtered") if a["filtered"] else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(files[-3:]), "file_hash": "", "filters": {"active": filters, "options": {}, "dimensions": dims}}
    ms = a["months"]
    cur = t["cur"]

    items = []
    if ms:
        items.append({"metric": "total", "text": c.t("x_total", v=money2(t["total"]), n=t["with_cost"], m=f"{L(t['first'])} – {L(t['last'])}", k=t["months"], mt=money2(t["maint"]), f=money2(t["fuel"]))})
        items.append({"metric": "cur", "text": c.t("x_cur", m=L(cur["period"]), v=money2(cur["total"]), n=cur["active"])})
        for m in ms:
            if m["partial"]:
                items.append({"metric": "partial", "text": c.t("x_partial", m=L(m["period"]))})
    if a["vehicles"] and a["vehicles"][0]["total"]:
        v0 = a["vehicles"][0]
        items.append({"metric": "top", "text": c.t("x_top", p=v0["plate"], v=money2(v0["total"]), s=pct(v0["share"]))})
    if a["categories"]:
        k0 = a["categories"][0]
        items.append({"metric": "cat", "text": c.t("x_cat", c=k0["name"], v=money2(k0["total"]), s=pct(k0["share"]))})
    if t["cost_per_km"] is not None:
        items.append({"metric": "cpk", "text": c.t("x_cpk", v=money2(t["cost_per_km"]), k=f"{t['km_known']:,.0f}")})
    if a["outliers"]:
        items.append({"metric": "outliers", "text": c.t("x_outliers", n=len(a["outliers"]), f=f"{th['outlier_factor']:g}")})
    if t["due_soon"]:
        items.append({"metric": "due", "text": c.t("x_due", n=t["due_soon"], k=f"{th['service_due_km']:g}")})
    if t["claims"]:
        items.append({"metric": "claims", "text": c.t("x_claims", o=money2(t["claims_original"]), c=money2(t["claims_company"]))})
    if t["maint_from_cats"]:
        items.append({"metric": "maint_basis", "text": c.t("x_maint_basis", n=t["maint_from_cats"])})
    if a["candidates"]:
        items.append({"metric": "cand", "text": c.t("x_cand", n=len(a["candidates"]))})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    if ms:
        sec.kpis = [{"label": c.t("k_total"), "value": money2(t["total"]), "sub": egp}, {"label": c.t("k_maint"), "value": money2(t["maint"]), "sub": egp}, {"label": c.t("k_fuel"), "value": money2(t["fuel"]), "sub": egp},
                    {"label": c.t("k_cur"), "value": money2(cur["total"]), "sub": L(cur["period"])}, {"label": c.t("k_vehicles"), "value": str(t["with_cost"]), "sub": ""},
                    {"label": c.t("k_cpk"), "value": money2(t["cost_per_km"]) if t["cost_per_km"] is not None else "—", "sub": egp}, {"label": c.t("k_due"), "value": str(t["due_soon"]), "sub": ""},
                    {"label": c.t("k_outliers"), "value": str(t["outliers"]), "sub": ""}]
        if t["claims"]:
            sec.kpis.append({"label": c.t("k_claims"), "value": money2(t["claims_original"]), "sub": egp})
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights += [{"severity": "info", "text": c.t("i_basis")}, {"severity": "info", "text": c.t("i_qty")}, {"severity": "info", "text": c.t("i_link")}]
    if focus:
        sec.insights.append({"severity": "info", "text": c.t("i_focus", m=L(focus))})
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- monthly + categories
    sec = ReportSection(c.t("s_monthly"), "monthly")
    if ms:
        sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_month"), "x": [S(m["period"]) for m in ms], "series": [
            {"name": c.t("c_maint"), "values": [float(m["maint"]) for m in ms]}, {"name": c.t("c_fuel"), "values": [float(m["fuel"]) for m in ms]}]})
        sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [col("p", c.t("c_period")), col("v", c.t("c_vehicles"), "int"), col("a", c.t("c_active"), "int"), col("t", c.t("c_total"), "money"),
                                                                                  col("m", c.t("c_maint"), "money"), col("f", c.t("c_fuel"), "money"), col("q", c.t("c_qty"), "num"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct"),
                                                                                  col("n", c.t("c_note"))],
                           "rows": [{"p": L(m["period"]), "v": m["vehicles"], "a": m["active"], "t": m["total"], "m": m["maint"], "f": m["fuel"], "q": m["fuel_qty"], "d": m.get("d"), "dp": m.get("dpct"),
                                     "n": c.t("partial") if m["partial"] else (c.t("large") if m["large"] else "")} for m in reversed(ms)]})
    rm.sections.append(sec)
    sec = ReportSection(c.t("s_categories"), "categories")
    cats = a["categories"]
    if cats:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_cat"), "x": [k["name"] for k in cats[:12]], "series": [{"name": c.t("c_total"), "values": [float(k["total"]) for k in cats[:12]]}]})
    sec.tables.append({"key": "categories", "title": c.t("t_cats"), "columns": [col("n", c.t("c_cat")), col("v", c.t("c_total"), "money"), col("s", c.t("c_share"), "pct"), col("c", c.t("c_cum"), "pct")],
                       "rows": [{"n": k["name"], "v": k["total"], "s": k["share"], "c": k["cum"]} for k in cats]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- vehicles
    sec = ReportSection(c.t("s_vehicles"), "vehicles")
    vr = [v for v in a["vehicles"] if v["total"]]
    top = vr[: int(th["top_n"])]
    if top:
        sec.charts.append({"type": "bar", "horizontal": True, "stacked": True, "title": c.t("ch_veh"), "x": [v["plate"] for v in top], "series": [
            {"name": c.t("c_maint"), "values": [float(v["maint"]) for v in top]}, {"name": c.t("c_fuel"), "values": [float(v["fuel"]) for v in top]}]})
    cps = [p for p in a["cost_periods"]]
    if len(cps) > 1 and vr:
        sec.charts.append({"type": "heatmap", "drill_rows": "vehicle", "title": c.t("ch_heat"), "rows": [v["plate"] for v in vr], "cols": [S(p) for p in cps],
                           "values": [[float(v["by_month"].get(p, 0)) or None for p in cps] for v in vr]})
    sec.tables.append({"key": "vehicles", "title": c.t("t_vehicles"), "columns": [col("p", c.t("c_plate")), col("ty", c.t("c_type")), col("n", c.t("c_months"), "int"), col("m", c.t("c_maint"), "money"), col("f", c.t("c_fuel"), "money"),
                                                                                col("t", c.t("c_total"), "money"), col("s", c.t("c_share"), "pct"), col("avg", c.t("c_avg"), "money"), col("mx", c.t("c_max")), col("km", c.t("c_km"), "int"),
                                                                                col("kmm", c.t("c_kmm"), "int"), col("cpk", c.t("c_cpk"), "money"), col("cons", c.t("c_cons"), "num"), col("src", c.t("c_sources"))],
                       "rows": [{"p": v["plate"], "ty": v["type"] or "—", "n": v["months"], "m": v["maint"], "f": v["fuel"], "t": v["total"], "s": v["share"], "avg": v["avg"], "mx": f"{S(v['max'][0])}: {money(v['max'][1])}" if v["max"] else "—",
                                 "km": v["km"], "kmm": v["km_months"], "cpk": v["cost_per_km"], "cons": v["consumption"], "src": " ".join(x[0].upper() for x in v["sources"])} for v in a["vehicles"]], "pdf_rows": 30})
    if a["outliers"]:
        sec.tables.append({"key": "outliers", "title": c.t("t_outliers"), "columns": [col("p", c.t("c_plate")), col("m", c.t("c_period")), col("t", c.t("c_total"), "money"), col("med", c.t("c_median"), "money"), col("f", c.t("c_factor"), "num"),
                                                                                     col("n", c.t("c_note"))] if admin else [col("p", c.t("c_plate")), col("m", c.t("c_period")), col("t", c.t("c_total"), "money"), col("med", c.t("c_median"), "money"), col("f", c.t("c_factor"), "num")],
                           "rows": [{"p": o["plate"], "m": L(o["period"]), "t": o["total"], "med": o["median"], "f": o["factor"], **({"n": o["note"]} if admin else {})} for o in a["outliers"][:30]], "pdf_rows": 25})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- fuel and distance
    sec = ReportSection(c.t("s_fuel"), "fuel")
    sec.insights.append({"severity": "info", "text": c.t("i_qty")})
    sec.insights.append({"severity": "info", "text": c.t("i_cpk")})
    prices = {}
    for s in data["summaries"]:
        prices.update(s.get("prices", {}))
    if prices:
        sec.tables.append({"key": "prices", "title": c.t("t_prices"), "columns": [col("p", c.t("c_period")), col("v", c.t("c_price"))],
                           "rows": [{"p": L(p), "v": " / ".join(f"{x:g}" for x in v)} for p, v in sorted(prices.items())]})
    if a["fuel_rows"]:
        sec.tables.append({"key": "fuel_rows", "title": c.t("t_fuel"), "columns": [col("v", c.t("c_plate")), col("p", c.t("c_period")), col("d", c.t("c_derived"), "num"), col("s", c.t("c_stated"), "num"), col("k", c.t("c_usage"), "num"),
                                                                                  col("c", c.t("c_cons"), "num"), col("r", c.t("c_rate"), "num")],
                           "rows": [{"v": r["plate"], "p": L(r["period"]), "d": r["derived"], "s": r["stated"], "k": r["km"], "c": r["consumption"], "r": r["stated_rate"]} for r in a["fuel_rows"]]})
    if a["km_rows"]:
        sec.tables.append({"key": "km_rows", "title": c.t("t_km"), "columns": [col("v", c.t("c_plate")), col("p", c.t("c_period")), col("a", c.t("c_statem"), "int"), col("b", c.t("c_usage"), "int"), col("d", c.t("c_daily"), "int"), col("o", c.t("c_odo"), "int")],
                           "rows": [{"v": r["plate"], "p": L(r["period"]), "a": r["statement"], "b": r["usage"], "d": r["daily"], "o": r["odometer"]} for r in a["km_rows"]], "pdf_rows": 30})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- service
    sec = ReportSection(c.t("s_service"), "service")
    if a["due"]:
        sec.tables.append({"key": "due", "title": c.t("t_due"), "columns": [col("v", c.t("c_plate")), col("p", c.t("c_period")), col("i", c.t("c_item")), col("o", c.t("c_odometer"), "int"), col("n", c.t("c_next"), "int"),
                                                                           col("r", c.t("c_rem"), "snum"), col("s", c.t("c_state"))],
                           "rows": [{"v": d["plate"], "p": L(d["period"]), "i": d["item"], "o": d["odometer"], "n": d["next_due"], "r": d["remaining"], "s": c.t("st_" + d["state"])} for d in a["due"]], "pdf_rows": 30})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- claims
    if a["claims"]:
        sec = ReportSection(c.t("s_claims"), "claims")
        sec.tables.append({"key": "claims", "title": c.t("t_claims"), "columns": [col("d", c.t("c_desc")), col("p", c.t("c_period")), col("o", c.t("c_orig"), "money"), col("i", c.t("c_ins"), "money"), col("c", c.t("c_co"), "money"), col("n", c.t("c_note"))],
                           "rows": [{"d": x["desc"], "p": L(x["period"]) if x.get("period") else "—", "o": x.get("original"), "i": x.get("insurer_share"), "c": x.get("company_share"), "n": x.get("note") or ""} for x in a["claims"]]})
        rm.sections.append(sec)

    # ---------------------------------------------------------------- coverage + candidates
    sec = ReportSection(c.t("s_coverage"), "coverage")
    sec.tables.append({"key": "coverage", "title": c.t("t_cov"), "columns": [col("v", c.t("c_plate"))] + [col(f"p{i}", S(p)) for i, p in enumerate(per)],
                       "rows": [{"v": r["plate"], **{f"p{i}": r["cells"].get(p, "") or "·" for i, p in enumerate(per)}} for r in a["coverage"]], "pdf_rows": 30})
    if a["candidates"]:
        sec.tables.append({"key": "candidates", "title": c.t("t_cand"), "columns": [col("n", c.t("c_number")), col("p", c.t("c_plates")), col("m", c.t("c_match"), "int")],
                           "rows": [{"n": x["number"], "p": " | ".join(x["plates"]), "m": x["km_matches"]} for x in a["candidates"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- versions + quality
    fld = lambda f: c.s.get("fld_" + f, f[4:] if f.startswith("cat:") else f)
    label_of = lambda x: x["label"] or x["key"]
    rm.sections.append(versions_section(c, data["versions"], data["changes"], label_of, fld, L))
    extra = []
    ctl = [x for s in data["summaries"] for x in s.get("controls", [])]
    if ctl:
        extra.append({"key": "controls", "title": c.t("t_ctl"), "note": c.t("ctl_note"), "columns": [col("p", c.t("c_period")), col("s", c.t("c_stated2"), "money"), col("c", c.t("c_computed"), "money"), col("d", c.t("c_diff"), "smoney")],
                      "rows": [{"p": L(x["period"]), "s": x["stated"], "c": x["computed"], "d": x["diff"]} for x in ctl]})
    half = [x for s in data["summaries"] for x in s.get("halfyear", [])]
    if half:
        extra.append({"key": "halfyear", "title": c.t("t_half"), "columns": [col("v", c.t("c_plate")), col("s", c.t("c_stated2"), "money"), col("c", c.t("c_computed"), "money"), col("d", c.t("c_diff"), "smoney")],
                      "rows": [{"v": x["plate"] or "Σ", "s": x["stated"], "c": x["computed"], "d": x["diff"]} for x in half]})
    rm.sections.append(quality_section(c, merged_issues(data["summaries"]), th, th_origin, [c.t("na_register"), c.t("na_measured"), c.t("na_driver"), c.t("na_before")], extra, [c.t("n_personal")]))
    return rm
