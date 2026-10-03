"""ReportModel for the paper-consumption analysis (distribution = consumption). Every sentence comes from computed values."""
from datetime import datetime, timezone
from decimal import Decimal

from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money, pct, period_label, smoney

T = {
    "ar": {
        "title": "استهلاك ورق التصوير والطباعة", "po": "أمر الشراء", "s_summary": "الملخص التنفيذي", "s_monthly": "الاستهلاك الشهري", "s_branches": "الفروع حسب الشهر",
        "s_hq": "إدارات المركز الرئيسي", "s_need": "الاستهلاك الموزَّع مقابل الاحتياج التقديري من الماكينات", "s_quality": "جودة البيانات والإعدادات",
        "k_cartons": "الكراتين الموزعة", "k_sheets": "الأوراق", "k_cost": "تكلفة الورق", "k_units": "جهات مستهلكة", "k_hq": "المركز الرئيسي", "k_avg": "متوسط الشهر",
        "k_po": "مطابقة أمر الشراء", "carton": "كرتونة", "sheet": "ورقة", "egp": "ج.م", "po_ok": "الموزع = المستلم", "po_diff": "فرق {d} كرتونة",
        "c_month": "الشهر", "c_cartons": "كراتين", "c_sheets": "أوراق", "c_cost": "التكلفة", "c_units": "الجهات", "c_mom": "التغير", "c_mompct": "التغير %",
        "c_pages": "نسخ الماكينات", "c_ppc": "نسخة لكل كرتونة موزعة", "c_cpp": "تكلفة ورق النسخة", "c_need": "احتياج تقديري (كراتين)", "c_cov": "الموزع من الاحتياج %",
        "c_gap": "الموزع − الاحتياج", "c_unit": "الجهة", "c_total": "الإجمالي", "c_share": "النسبة %", "c_cum": "التراكمي %", "c_deliv": "مرات التوزيع", "c_rank": "الترتيب",
        "c_avg": "متوسط شهري", "c_match": "المطابقة", "c_mbranch": "فرع الماكينات", "c_key": "البيان", "c_val": "القيمة", "c_source": "المصدر", "c_issue": "الملاحظة",
        "c_sev": "الأهمية", "c_count": "العدد", "c_examples": "أمثلة", "c_name": "الإعداد", "c_po": "أمر الشراء", "c_recv": "تاريخ الاستلام", "c_recvq": "المستلم",
        "c_dist": "الموزع", "c_stated": "إجمالي الكشف", "c_price": "سعر الكرتونة", "c_win": "نافذة السعر", "c_file": "الملف", "c_pct": "نسبة الجهة %", "c_pages1": "نسخ الماكينات",
        "t_month": "كراتين وتكلفة كل شهر", "t_cart": "الكراتين حسب الجهة والشهر", "t_cost": "تكلفة الورق حسب الجهة والشهر", "t_hq": "استهلاك إدارات المركز الرئيسي",
        "t_need": "مقارنة شهرية: الموزع مقابل الاحتياج التقديري", "t_cmp": "مقارنة حسب الجهة (حيث أمكنت المطابقة بالاسم)", "t_po": "أوامر الشراء المرفوعة", "t_issues": "ملاحظات جودة البيانات",
        "t_settings": "الإعدادات المستخدمة", "t_prices": "نوافذ أسعار الكرتونة", "ch_month": "الكراتين الموزعة شهريًا", "ch_cost": "تكلفة الورق شهريًا (ج.م)",
        "ch_top": "أعلى الجهات استهلاكًا (كراتين)", "ch_hq": "إدارات المركز الرئيسي (كراتين)",
        "hq": "المركز الرئيسي", "hq_general": "المركز الرئيسي (بدون تحديد إدارة)", "f_branches": "الجهة", "f_months": "الشهر",
        "m_exact": "اسم مطابق", "m_name_contains": "مطابقة بالاسم (للمراجعة)", "m_ambiguous": "أكثر من احتمال", "m_none": "لا مطابقة",
        "sev_critical": "حرج", "sev_warning": "تنبيه", "sev_info": "للعلم",
        "x_total": "وُزّع {c} كرتونة ورق ({s} ورقة) على {u} جهة خلال {m} أشهر، بتكلفة {cost} ج.م (ورق معفى من الضريبة، بسعر نافذة الشراء).",
        "x_month": "أعلى شهر استهلاكًا {m} ({c} كرتونة، {cost} ج.م) وأقلها {lm} ({lc} كرتونة).",
        "x_top": "أعلى جهة استهلاكًا «{n}» ({c} كرتونة، {p} من الإجمالي)؛ وأعلى 10 جهات تمثل {t} من الإجمالي.",
        "x_hq": "المركز الرئيسي استهلك {c} كرتونة ({p}) موزعة على {n} إدارة؛ الأعلى «{d}» ({dc} كرتونة).",
        "x_ppc": "في {m} وُزّع {c} كرتونة مقابل {pages} نسخة مسجلة على الماكينات، أي ≈{ppc} نسخة لكل كرتونة موزعة، وتكلفة ورق ≈{cpp} ج.م للنسخة.",
        "x_po": "أمر الشراء {po}: الموزع {d} كرتونة مقابل {r} مستلمة.",
        "i_dist": "الاستهلاك = ما وُزّع للجهات حسب كشف التوزيع (وليس الاستخدام الفعلي للورق داخل الجهة)؛ التكلفة = الكراتين × سعر نافذة الشراء، والورق معفى من الضريبة.",
        "i_need": "الاحتياج التقديري = نسخ الماكينات ÷ {pps} نسخة لكل ورقة ÷ {spc} ورقة لكل كرتونة؛ وهو تقدير مستقل ولا يغيّر الاستهلاك الموزَّع. قيمة «نسخ لكل ورقة» ({pps}) {origin}.",
        "i_origin_default": "قيمة ابتدائية لم تُعتمد بعد (تُعدَّل من الإعدادات)", "i_origin_custom": "قيمة معتمدة من الإعدادات",
        "i_noprice": "لا توجد نافذة سعر تغطي تاريخ استلام أمر الشراء؛ التكلفة غير محسوبة له.",
        "i_filtered": "العرض الحالي مفلتر؛ مقارنة نسخ الماكينات الإجمالية لا تُعرض مع الفلاتر.",
        "i_nopages": "لا توجد كشوف استهلاك ماكينات للأشهر المعروضة؛ المقارنة بالاحتياج غير محسوبة (يلزم رفع الكشف الشهري).",
        "i_boundary": "حدود نوافذ الأسعار (منتصف الشهر) ثابتة في الإعدادات ويمكن تعديلها.",
        "i_cmp_review": "المطابقة بين أسماء كشف التوزيع وكشف الماكينات بالاسم فقط؛ راجع الصفوف المعلَّمة قبل الاعتماد.",
        "i_hq_note": "تُعرض كل إدارة بالمركز الرئيسي منفصلة؛ التهجئات المختلفة لنفس الإدارة جُمعت بنص ما بعد «المركز الرئيسي».",
        "p_sheets_per_carton": "أوراق الكرتونة", "p_pages_per_sheet": "نسخ لكل ورقة", "p_prices_vat_exempt": "الأسعار معفاة من الضريبة", "yes": "نعم", "no": "لا",
    },
    "en": {
        "title": "Copier paper consumption", "po": "Purchase order", "s_summary": "Executive summary", "s_monthly": "Monthly consumption", "s_branches": "Branches by month",
        "s_hq": "Head Office departments", "s_need": "Distributed consumption vs the need implied by the machines", "s_quality": "Data quality and settings",
        "k_cartons": "Cartons distributed", "k_sheets": "Sheets", "k_cost": "Paper cost", "k_units": "Consuming units", "k_hq": "Head Office", "k_avg": "Monthly average",
        "k_po": "PO control", "carton": "cartons", "sheet": "sheets", "egp": "EGP", "po_ok": "Distributed = received", "po_diff": "{d} cartons difference",
        "c_month": "Month", "c_cartons": "Cartons", "c_sheets": "Sheets", "c_cost": "Cost", "c_units": "Units", "c_mom": "Change", "c_mompct": "Change %",
        "c_pages": "Machine pages", "c_ppc": "Pages per distributed carton", "c_cpp": "Paper cost per page", "c_need": "Estimated need (cartons)", "c_cov": "Distributed of need %",
        "c_gap": "Distributed − need", "c_unit": "Unit", "c_total": "Total", "c_share": "Share %", "c_cum": "Cumulative %", "c_deliv": "Deliveries", "c_rank": "Rank",
        "c_avg": "Monthly avg", "c_match": "Match", "c_mbranch": "Machines branch", "c_key": "Item", "c_val": "Value", "c_source": "Source", "c_issue": "Issue",
        "c_sev": "Severity", "c_count": "Count", "c_examples": "Examples", "c_name": "Setting", "c_po": "PO", "c_recv": "Receipt date", "c_recvq": "Received",
        "c_dist": "Distributed", "c_stated": "Statement total", "c_price": "Carton price", "c_win": "Price window", "c_file": "File", "c_pct": "Unit share %", "c_pages1": "Machine pages",
        "t_month": "Cartons and cost per month", "t_cart": "Cartons by unit and month", "t_cost": "Paper cost by unit and month", "t_hq": "Head Office department consumption",
        "t_need": "Monthly: distributed vs estimated need", "t_cmp": "By unit (where the name could be matched)", "t_po": "Uploaded purchase orders", "t_issues": "Data-quality notes",
        "t_settings": "Settings used", "t_prices": "Carton price windows", "ch_month": "Cartons distributed per month", "ch_cost": "Paper cost per month (EGP)",
        "ch_top": "Top consuming units (cartons)", "ch_hq": "Head Office departments (cartons)",
        "hq": "Head Office", "hq_general": "Head Office (department not stated)", "f_branches": "Unit", "f_months": "Month",
        "m_exact": "Same name", "m_name_contains": "Matched by name (review)", "m_ambiguous": "Several candidates", "m_none": "No match",
        "sev_critical": "Critical", "sev_warning": "Warning", "sev_info": "Info",
        "x_total": "{c} cartons of paper ({s} sheets) were distributed to {u} units over {m} months, costing {cost} EGP (VAT-exempt paper, at the purchase window's price).",
        "x_month": "Highest month {m} ({c} cartons, {cost} EGP); lowest {lm} ({lc} cartons).",
        "x_top": "Top unit «{n}» ({c} cartons, {p} of total); the top 10 units account for {t}.",
        "x_hq": "Head Office took {c} cartons ({p}) across {n} departments; the largest is «{d}» ({dc} cartons).",
        "x_ppc": "In {m}, {c} cartons were distributed against {pages} pages recorded on the machines: ≈{ppc} pages per distributed carton and ≈{cpp} EGP of paper per page.",
        "x_po": "Purchase order {po}: {d} cartons distributed vs {r} received.",
        "i_dist": "Consumption = what the distribution statement handed to each unit (not the paper actually used inside the unit); cost = cartons × the purchase window's price, paper is VAT-exempt.",
        "i_need": "Estimated need = machine pages ÷ {pps} pages per sheet ÷ {spc} sheets per carton; it is a separate estimate and does not change the distributed consumption. 'Pages per sheet' ({pps}) is {origin}.",
        "i_origin_default": "an initial value, not yet confirmed (editable in settings)", "i_origin_custom": "a value set in settings",
        "i_noprice": "No price window covers the purchase order's receipt date; its cost is not calculated.",
        "i_filtered": "This view is filtered; the all-machines comparison is not shown with filters.",
        "i_nopages": "No machine consumption statement for the months shown; the need comparison is not calculated (upload the monthly statement).",
        "i_boundary": "Price-window boundaries (mid-month) are settings and can be edited.",
        "i_cmp_review": "Distribution names are matched to machine-statement names by name only; review the flagged rows before relying on them.",
        "i_hq_note": "Each Head Office department is shown separately; different spellings of one department are grouped by the text after 'المركز الرئيسي'.",
        "p_sheets_per_carton": "Sheets per carton", "p_pages_per_sheet": "Pages per sheet", "p_prices_vat_exempt": "Prices are VAT-exempt", "yes": "Yes", "no": "No",
    },
}


class P:
    def __init__(self, lang):
        self.lang, self.s = lang, T[lang]

    def t(self, k, **kw):
        return self.s[k].format(**kw) if kw else self.s[k]

    def unit(self, u) -> str:
        if not u["hq"]:
            return u["name"]
        return f"{self.t('hq')} - {u['department']}" if u["department"] else self.t("hq_general")


def _mlabel(lang, m, short=False):
    return period_label(lang, m, short)


def build_paper_report(a: dict, statements: list[dict], lang: str, origin: dict, filters: dict, dims: list[dict], any_pages: bool) -> ReportModel:
    p = P(lang)
    months, units, tot = a["months"], a["units"], a["totals"]
    rm = ReportModel(title=p.t("title"), period_label=f"{_mlabel(lang, months[0])} – {_mlabel(lang, months[-1])}" if months else "", sections=[], lang=lang)
    rm.subtitle = f"{p.t('po')}: " + ", ".join(str(s.get("po_no") or "—") for s in statements) + (" · filtered" if filters else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(s["file_name"] for s in statements[:3]), "file_hash": "",
               "filters": {"active": filters, "options": {}, "dimensions": dims}}
    params = a["params"]
    spc, pps = params["sheets_per_carton"], params["pages_per_sheet"]
    by = a["by_month"]
    # -------------------------------------------------------------- summary
    items = [{"metric": "total", "text": p.t("x_total", c=money(tot["cartons"]), s=money(tot["sheets"]), u=len(units), m=len(months), cost=money(tot["cost"]))}]
    if len(by) >= 2:
        hi, lo = max(by, key=lambda r: r["cartons"]), min(by, key=lambda r: r["cartons"])
        items.append({"metric": "months", "text": p.t("x_month", m=_mlabel(lang, hi["period"]), c=money(hi["cartons"]), cost=money(hi["cost"]),
                                                      lm=_mlabel(lang, lo["period"]), lc=money(lo["cartons"]))})
    if units:
        top = units[0]
        items.append({"metric": "top", "text": p.t("x_top", n=p.unit(top), c=money(top["cartons"]), p=pct(top["share"]), t=pct(units[min(9, len(units) - 1)]["cum_share"]))})
    hq = a["head_office"]
    if hq:
        items.append({"metric": "hq", "text": p.t("x_hq", c=money(a["hq_summary"]["cartons"]), p=pct(a["hq_summary"]["share"]), n=len(hq), d=p.unit(hq[0]), dc=money(hq[0]["cartons"]))})
    for r in by:
        if r["pages"]:
            items.append({"metric": "ppc", "text": p.t("x_ppc", m=_mlabel(lang, r["period"]), c=money(r["cartons"]), pages=money(r["pages"]), ppc=money(r["pages_per_carton"]),
                                                      cpp=f"{r['cost_per_page']:.3f}" if r["cost_per_page"] is not None else "—")})
    for s in statements:
        dist = sum((r["cartons"] for r in s["rows"]), Decimal(0))
        if s["received_cartons"] is not None and not filters:
            items.append({"metric": "po", "text": p.t("x_po", po=s.get("po_no") or "—", d=money(dist), r=money(s["received_cartons"]))})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(p.t("s_summary"), "summary")
    ctrl = [s for s in statements if s["received_cartons"] is not None]
    diff = sum((sum((r["cartons"] for r in s["rows"]), Decimal(0)) - s["received_cartons"] for s in ctrl), Decimal(0)) if ctrl else None
    sec.kpis = [{"label": p.t("k_cartons"), "value": money(tot["cartons"]), "sub": p.t("carton")},
                {"label": p.t("k_sheets"), "value": money(tot["sheets"]), "sub": f"{money(spc)} / {p.t('carton')}"},
                {"label": p.t("k_cost"), "value": money(tot["cost"]) if tot["cost_complete"] else "—", "sub": p.t("egp")},
                {"label": p.t("k_units"), "value": str(len(units)), "sub": f"{tot['branches']} + {tot['hq_units']} HQ"},
                {"label": p.t("k_hq"), "value": money(a["hq_summary"]["cartons"]), "sub": pct(a["hq_summary"]["share"])},
                {"label": p.t("k_avg"), "value": money(tot["cartons"] / len(months)) if months else "—", "sub": p.t("carton")}]
    if diff is not None and not filters:
        sec.kpis.append({"label": p.t("k_po"), "value": p.t("po_ok") if diff == 0 else p.t("po_diff", d=smoney(diff)), "sub": "", "tone": "" if diff == 0 else "up"})
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    rm.sections.append(sec)
    # -------------------------------------------------------------- monthly
    sec = ReportSection(p.t("s_monthly"), "monthly")
    x = [_mlabel(lang, r["period"], True) for r in by]
    sec.charts.append({"type": "bar", "title": p.t("ch_month"), "x": x, "series": [{"name": p.t("c_cartons"), "values": [float(r["cartons"]) for r in by]}]})
    if tot["cost_complete"]:
        sec.charts.append({"type": "bar", "title": p.t("ch_cost"), "x": x, "series": [{"name": p.t("c_cost"), "values": [float(r["cost"]) for r in by]}]})
    sec.tables.append({"key": "monthly", "title": p.t("t_month"), "columns": [
        col("period", p.t("c_month")), col("cartons", p.t("c_cartons"), "int"), col("sheets", p.t("c_sheets"), "int"), col("cost", p.t("c_cost"), "money"),
        col("units", p.t("c_units"), "int"), col("mom", p.t("c_mom"), "smoney"), col("mompct", p.t("c_mompct"), "spct")],
        "rows": [{"period": _mlabel(lang, r["period"]), "cartons": r["cartons"], "sheets": r["sheets"], "cost": r["cost"] if tot["cost_complete"] else None, "units": r["units"],
                  "mom": r.get("cartons_mom"), "mompct": r.get("cartons_mom_pct")} for r in by]})
    rm.sections.append(sec)
    # -------------------------------------------------------------- branches x month
    sec = ReportSection(p.t("s_branches"), "branches")
    sec.charts.append({"type": "bar", "horizontal": True, "title": p.t("ch_top"), "x": [p.unit(u) for u in units[:10]], "series": [{"name": p.t("c_cartons"), "values": [float(u["cartons"]) for u in units[:10]]}]})
    mcols = [col(f"m{i}", _mlabel(lang, m, True), "int") for i, m in enumerate(months)]
    base = [col("rank", p.t("c_rank"), "int"), col("unit", p.t("c_unit"))]
    sec.tables.append({"key": "unit_cartons", "title": p.t("t_cart"), "columns": base + mcols + [
        col("total", p.t("c_total"), "int"), col("share", p.t("c_share"), "pct"), col("cum", p.t("c_cum"), "pct"), col("deliv", p.t("c_deliv"), "int")],
        "rows": [{"rank": u["rank"], "unit": p.unit(u), **{f"m{i}": u["by_month"].get(m) for i, m in enumerate(months)}, "total": u["cartons"], "share": u["share"],
                  "cum": u["cum_share"], "deliv": u["deliveries"]} for u in units], "pdf_rows": 45})
    if tot["cost_complete"]:
        price_by_month = {r["period"]: (r["cost"] / r["cartons"] if r["cartons"] else None) for r in by}
        sec.tables.append({"key": "unit_cost", "title": p.t("t_cost"), "columns": [col("unit", p.t("c_unit"))] + [col(f"m{i}", _mlabel(lang, m, True), "money") for i, m in enumerate(months)] + [col("total", p.t("c_total"), "money")],
                           "rows": [{"unit": p.unit(u), **{f"m{i}": (u["by_month"][m] * price_by_month[m]) if m in u["by_month"] and price_by_month[m] is not None else None for i, m in enumerate(months)},
                                     "total": u["cost"]} for u in units], "pdf_rows": 45})
    rm.sections.append(sec)
    # -------------------------------------------------------------- head office
    sec = ReportSection(p.t("s_hq"), "head_office")
    if hq:
        sec.insights.append({"severity": "info", "text": p.t("i_hq_note")})
        sec.charts.append({"type": "bar", "horizontal": True, "title": p.t("ch_hq"), "x": [p.unit(u) for u in hq], "series": [{"name": p.t("c_cartons"), "values": [float(u["cartons"]) for u in hq]}]})
        sec.tables.append({"key": "hq", "title": p.t("t_hq"), "columns": [col("unit", p.t("c_unit"))] + mcols + [
            col("total", p.t("c_total"), "int"), col("pct", p.t("c_pct"), "pct"), col("cost", p.t("c_cost"), "money")],
            "rows": [{"unit": p.unit(u), **{f"m{i}": u["by_month"].get(m) for i, m in enumerate(months)}, "total": u["cartons"],
                      "pct": float(u["cartons"] / a["hq_summary"]["cartons"] * 100) if a["hq_summary"]["cartons"] else None,
                      "cost": u["cost"] if tot["cost_complete"] else None} for u in hq]})
    rm.sections.append(sec)
    # -------------------------------------------------------------- need vs distributed
    sec = ReportSection(p.t("s_need"), "need")
    sec.insights.append({"severity": "info", "text": p.t("i_need", pps=pps, spc=money(spc), origin=p.t("i_origin_" + ("custom" if origin.get("pages_per_sheet") == "custom" else "default")))})
    with_pages = [r for r in by if r["pages"]]
    if with_pages:
        sec.tables.append({"key": "need", "title": p.t("t_need"), "columns": [
            col("period", p.t("c_month")), col("cartons", p.t("c_cartons"), "int"), col("pages", p.t("c_pages"), "int"), col("ppc", p.t("c_ppc"), "int"),
            col("cpp", p.t("c_cpp"), "money3"), col("need", p.t("c_need"), "num"), col("gap", p.t("c_gap"), "snum"), col("cov", p.t("c_cov"), "pct")],
            "rows": [{"period": _mlabel(lang, r["period"]), "cartons": r["cartons"], "pages": r["pages"], "ppc": r["pages_per_carton"], "cpp": r["cost_per_page"],
                      "need": r["need_cartons"], "gap": r["need_gap"], "cov": r["coverage"]} for r in with_pages]})
    elif not filters:
        sec.insights.append({"severity": "info", "text": p.t("i_nopages")})
    if filters and any(a["compare"]):
        sec.insights.append({"severity": "info", "text": p.t("i_filtered")})
    if a["compare"]:
        sec.insights.append({"severity": "warning", "text": p.t("i_cmp_review")})
        sec.tables.append({"key": "compare", "title": p.t("t_cmp"), "columns": [
            col("period", p.t("c_month")), col("unit", p.t("c_unit")), col("cartons", p.t("c_cartons"), "int"), col("pages", p.t("c_pages1"), "int"),
            col("ppc", p.t("c_ppc"), "int"), col("need", p.t("c_need"), "num"), col("gap", p.t("c_gap"), "snum"), col("match", p.t("c_match")), col("mb", p.t("c_mbranch"))],
            "rows": [{"period": _mlabel(lang, r["period"]), "unit": p.unit({"hq": r["hq"], "name": r["unit"], "department": next((u["department"] for u in units if u["name"] == r["unit"] and u["hq"]), None)}),
                      "cartons": r["cartons"], "pages": r["pages"], "ppc": r["pages_per_carton"], "need": r["need_cartons"], "gap": r["gap"],
                      "match": p.t("m_" + r["match"]), "mb": r["machine_branch"] or ""} for r in a["compare"]], "pdf_rows": 40})
    rm.sections.append(sec)
    # -------------------------------------------------------------- quality
    sec = ReportSection(p.t("s_quality"), "quality")
    sec.insights.append({"severity": "info", "text": p.t("i_dist")})
    sec.insights.append({"severity": "info", "text": p.t("i_boundary")})
    if any(n["code"] == "no_price_window" for n in a["notes"]):
        sec.insights.append({"severity": "warning", "text": p.t("i_noprice")})
    po_rows = []
    from app.modules.copier_analysis.paper import price_for
    for s in statements:
        dist = sum((r["cartons"] for r in s["rows"]), Decimal(0))
        pr = price_for(params, s["receipt_date"] or next((r["distributed_on"] for r in s["rows"] if r["distributed_on"]), None))
        po_rows.append({"po": s.get("po_no") or "—", "recv_date": s["receipt_date"].isoformat() if s["receipt_date"] else "", "recv": s["received_cartons"],
                        "dist": dist, "stated": s["stated_total"], "price": pr["price_per_carton"] if pr else None,
                        "win": f"{pr['from']} → {pr['to']}" if pr else "", "file": s["file_name"]})
    sec.tables.append({"key": "po", "title": p.t("t_po"), "columns": [col("po", p.t("c_po")), col("recv_date", p.t("c_recv")), col("recv", p.t("c_recvq"), "int"),
                                                                      col("dist", p.t("c_dist"), "int"), col("stated", p.t("c_stated"), "int"), col("price", p.t("c_price"), "money"),
                                                                      col("win", p.t("c_win")), col("file", p.t("c_file"))], "rows": po_rows})
    issues = [{**i, "po": s.get("po_no")} for s in statements for i in s["issues"]]
    sec.tables.append({"key": "issues", "title": p.t("t_issues"), "columns": [col("po", p.t("c_po")), col("message", p.t("c_issue")), col("severity", p.t("c_sev")),
                                                                              col("count", p.t("c_count"), "int"), col("examples", p.t("c_examples"))],
                       "rows": [{"po": i["po"] or "—", "message": i["message"], "severity": p.t("sev_" + i["severity"]), "count": i["count"], "examples": " | ".join(i["examples"][:4])}
                                for i in issues], "pdf_rows": 25})
    sec.tables.append({"key": "settings", "title": p.t("t_settings"), "columns": [col("name", p.t("c_name")), col("value", p.t("c_val")), col("source", p.t("c_source"))],
                       "rows": [{"name": p.t("p_sheets_per_carton"), "value": spc, "source": origin["sheets_per_carton"]},
                                {"name": p.t("p_pages_per_sheet"), "value": pps, "source": origin["pages_per_sheet"]},
                                {"name": p.t("p_prices_vat_exempt"), "value": p.t("yes") if params["prices_vat_exempt"] else p.t("no"), "source": origin["prices_vat_exempt"]}]
                       + [{"name": f"{p.t('t_prices')}: {w['from']} → {w['to']}", "value": w["price_per_carton"], "source": origin["prices"]} for w in params["prices"]]})
    rm.sections.append(sec)
    return rm
