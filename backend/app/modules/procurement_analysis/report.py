"""ReportModel for procurement register analytics. Sentences are generated from computed numbers only; what the registers do not
support is stated as «not available»."""
from datetime import datetime, timezone
from decimal import Decimal

from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "تحليل المشتريات (أوامر الشراء والاحتياج والتسليم للمالية)", "s_summary": "الملخص التنفيذي", "s_monthly": "الاتجاه الشهري", "s_suppliers": "الموردون",
        "s_categories": "التصنيفات", "s_departments": "الإدارات الطالبة وسير الطلبات", "s_finance": "التسليم للإدارة المالية والمدد", "s_quality": "جودة البيانات والإعدادات",
        "source": "المصادر", "filtered": "عرض مفلتر", "egp": "ج.م", "no_supplier": "بدون مورد في السجل", "no_cat": "بدون تصنيف", "unspec": "غير محدد",
        "k_po": "أوامر الشراء", "k_value": "قيمة أوامر الشراء (المسعّرة)", "k_avg": "متوسط قيمة الأمر", "k_sup": "موردون", "k_canc": "أوامر ملغاة (معلَّمة)", "k_req": "إشعارات الاحتياج",
        "k_conv": "إشعارات صدر لها أمر شراء", "k_memo": "مذكرات التسليم للمالية", "k_memo_po": "مذكرات أوامر الشراء", "k_memo_svc": "مذكرات الخدمات (بدون أمر شراء)", "k_handed": "المسلَّم للمالية حسب سجل الأوامر",
        "k_rem": "المتبقي حسب سجل الأوامر", "ords": "أمر", "reqs": "إشعار",
        "c_month": "الشهر", "c_po": "الأوامر", "c_value": "القيمة", "c_d": "التغير", "c_dpct": "التغير %", "c_req": "إشعارات الاحتياج", "c_memo_po": "تسليم المالية: أوامر", "c_memo_svc": "تسليم المالية: خدمات",
        "c_note": "ملاحظة", "c_rank": "الترتيب", "c_supplier": "المورد", "c_n": "العدد", "c_share": "النسبة %", "c_cum": "التراكمي %", "c_avg": "المتوسط", "c_cat": "التصنيف",
        "c_dept": "الإدارة", "c_urgent": "عاجل", "c_withpo": "صدر لها أمر", "c_conv": "نسبة التحويل %", "c_status": "الحالة", "c_key": "البيان", "c_val": "القيمة", "c_type": "النوع",
        "c_amount": "المبلغ", "c_median": "الوسيط (يوم)", "c_p90": "المئين 90 (يوم)", "c_pairs": "عدد الأزواج", "c_neg": "سالب", "c_long": "أطول من الحد", "c_cov": "حالة التسليم",
        "c_code": "الكود", "c_sev": "الأهمية", "c_examples": "أمثلة", "c_file": "الملف", "c_rows": "الصفوف", "c_loaded": "المحمّل", "c_held": "المحجوز", "c_name": "الإعداد", "c_origin": "المصدر",
        "c_branch": "الفرع", "c_issue": "الملاحظة",
        "t_months": "المؤشرات حسب شهر تاريخ الأمر", "t_sup": "أعلى الموردين قيمة", "t_supcat": "تصنيف المورد", "t_cat": "تصنيف أمر الشراء (كما في السجل)", "t_dept": "الإدارات الطالبة",
        "t_reqstatus": "حالة إشعارات الاحتياج (كما في السجل)", "t_prio": "أولوية الإشعارات", "t_postatus": "حالة أوامر الشراء (كما في السجل)", "t_lead": "المدد بين المراحل", "t_cov": "تغطية التسليم للمالية لكل أمر",
        "t_memocat": "مذكرات التسليم للمالية حسب التصنيف", "t_attr": "نسبة ربط الأوامر بالفروع", "t_bval": "قيمة الأوامر حسب الفرع (المؤكد فقط)", "t_batches": "ما حُمّل من الملفات", "t_issues": "ملاحظات جودة البيانات (مفتوحة)",
        "t_settings": "الإعدادات المستخدمة", "t_na": "غير متاح (لا تدعمه السجلات)",
        "ch_month": "قيمة أوامر الشراء شهريًا", "ch_sup": "أعلى الموردين قيمة", "ch_cat": "القيمة حسب تصنيف الأمر",
        "lead_req": "من تاريخ إشعار الاحتياج إلى تاريخ أمر الشراء", "lead_memo": "من تاريخ أمر الشراء إلى تاريخ المذكرة للمالية",
        "cov_none": "لم يُسلَّم شيء", "cov_partial": "تسليم جزئي", "cov_full": "تسليم كامل", "cov_exceeds": "المسلَّم أكبر من إجمالي الأمر", "cov_no_total": "بدون إجمالي في السجل",
        "memo_po": "أوامر شراء", "memo_service": "خدمات", "partial": "شهر غير مكتمل (آخر تاريخ في البيانات قبل نهايته)",
        "attr_auto": "مربوط بيقين بفرع/مقر", "attr_review": "يحتاج مراجعة (لا دليل صريح على الفرع)", "attr_other": "غير مصنف", "branch_unalloc": "Unallocated / يحتاج مراجعة", "hq": "المركز الرئيسي",
        "x_total": "{n} أمر شراء ({p} منها مسعّر) بقيمة {v} ج.م، بمتوسط {a} ج.م للأمر، من {s} مورد.",
        "x_peak": "أعلى شهر قيمة {m} ({v} ج.م، {n} أمر).", "x_conc": "أعلى {k} موردين يمثلون {c} من القيمة، وأكبرهم «{s}» ({sp}).",
        "x_cat": "أعلى تصنيف قيمة «{c}» ({v} ج.م، {p}).", "x_req": "{n} إشعار احتياج، صدر لـ {w} منها أمر شراء ({c}).",
        "x_lead": "الوسيط من الإشعار إلى الأمر {a} يومًا، ومن الأمر إلى المذكرة للمالية {b} يومًا.",
        "x_memo": "التسليم للمالية: {n} مذكرة بإجمالي {v} ج.م، منها {pv} ج.م لأوامر شراء و{sv} ج.م لخدمات بدون أمر.",
        "x_unpriced": "{n} أمر بدون إجمالي في السجل: يُحسب كأمر ولا يُحسب في القيمة (ولا يُعامل كصفر).",
        "x_canc": "{n} أمر معلَّم كملغي بقيمة {v} ج.م مذكورة ضمن القيمة الإجمالية وتظهر هنا منفصلة؛ لم يُحذف شيء.",
        "x_canc_nov": "{n} أمر معلَّم كملغي وليس له إجمالي في السجل؛ لم يُحذف شيء.",
        "x_cov": "حسب سجل الأوامر: {f} أمر مسلَّم كاملاً، و{p} جزئيًا، و{z} بلا تسليم، و{e} المسلَّم فيها أكبر من الإجمالي.",
        "x_attr": "{r} أمر من {n} بلا دليل صريح على الفرع (يظهر Unallocated)؛ لا يُوزَّع على فرع بالتخمين.",
        "x_partial": "آخر شهر في البيانات غير مكتمل؛ لا تُقارن به كشهر كامل.",
        "i_basis": "القيمة = إجمالي الأمر كما هو مذكور في سجل الأوامر. «المسلَّم للمالية» و«مكتمل وتم السداد» كلام السجل نفسه وليسا سدادًا مؤكدًا من البنك.",
        "i_exclusion": "لم تُحدَّد بعد قواعد استبعاد حسب الحالة؛ لذا تدخل كل الأوامر ذات الإجمالي في القيمة، والملغاة تظهر منفصلة.",
        "i_filtered": "العرض مفلتر: الشهور بتاريخ كل كيان (الأمر/الإشعار/المذكرة)، والمورد على الأوامر ومذكراتها وإشعاراتها، والإدارة على الإشعارات وأوامرها.",
        "i_branch": "الفرع لا يُحدَّد إلا بدليل صريح في نص الأمر؛ غير ذلك Unallocated.",
        "na_payments": "سداد البنك الفعلي وتواريخه: لا يوجد سجل مدفوعات", "na_lines": "أصناف وكميات وأسعار الوحدات: السجل على مستوى رأس الأمر", "na_savings": "الوفورات ومقارنة العروض: لا توجد بيانات عروض أسعار",
        "sev_error": "خطأ", "sev_warning": "تنبيه", "sev_info": "للعلم",
    },
    "en": {
        "title": "Procurement analysis (purchase orders, requisitions, finance handover)", "s_summary": "Executive summary", "s_monthly": "Monthly trend", "s_suppliers": "Suppliers",
        "s_categories": "Categories", "s_departments": "Requesting departments and order flow", "s_finance": "Finance handover and lead times", "s_quality": "Data quality and settings",
        "source": "Sources", "filtered": "Filtered view", "egp": "EGP", "no_supplier": "No supplier in the register", "no_cat": "No category", "unspec": "Not stated",
        "k_po": "Purchase orders", "k_value": "PO value (priced)", "k_avg": "Average PO value", "k_sup": "Suppliers", "k_canc": "Cancelled POs (flagged)", "k_req": "Requisitions",
        "k_conv": "Requisitions with a PO", "k_memo": "Finance handover memos", "k_memo_po": "PO memos", "k_memo_svc": "Service memos (no PO)", "k_handed": "Handed to Finance per the PO register",
        "k_rem": "Remaining per the PO register", "ords": "POs", "reqs": "requisitions",
        "c_month": "Month", "c_po": "POs", "c_value": "Value", "c_d": "Change", "c_dpct": "Change %", "c_req": "Requisitions", "c_memo_po": "Handed to Finance: POs", "c_memo_svc": "Handed to Finance: services",
        "c_note": "Note", "c_rank": "Rank", "c_supplier": "Supplier", "c_n": "Count", "c_share": "Share %", "c_cum": "Cumulative %", "c_avg": "Average", "c_cat": "Category",
        "c_dept": "Department", "c_urgent": "Urgent", "c_withpo": "With a PO", "c_conv": "Conversion %", "c_status": "Status", "c_key": "Item", "c_val": "Value", "c_type": "Type",
        "c_amount": "Amount", "c_median": "Median (days)", "c_p90": "90th pct (days)", "c_pairs": "Pairs", "c_neg": "Negative", "c_long": "Above the limit", "c_cov": "Handover status",
        "c_code": "Code", "c_sev": "Severity", "c_examples": "Examples", "c_file": "File", "c_rows": "Rows", "c_loaded": "Loaded", "c_held": "Held", "c_name": "Setting", "c_origin": "Origin",
        "c_branch": "Branch", "c_issue": "Issue",
        "t_months": "Indicators by PO-date month", "t_sup": "Top suppliers by value", "t_supcat": "Supplier category", "t_cat": "PO category (as in the register)", "t_dept": "Requesting departments",
        "t_reqstatus": "Requisition status (as in the register)", "t_prio": "Requisition priority", "t_postatus": "PO status (as in the register)", "t_lead": "Lead times between stages", "t_cov": "Finance handover coverage per PO",
        "t_memocat": "Finance handover memos by category", "t_attr": "Branch attribution of POs", "t_bval": "PO value by branch (confirmed only)", "t_batches": "What was loaded from the files", "t_issues": "Data-quality notes (open)",
        "t_settings": "Settings used", "t_na": "Not available (the registers do not support it)",
        "ch_month": "PO value per month", "ch_sup": "Top suppliers by value", "ch_cat": "Value by PO category",
        "lead_req": "Requisition date → PO date", "lead_memo": "PO date → memo date to Finance",
        "cov_none": "Nothing handed over", "cov_partial": "Partly handed over", "cov_full": "Fully handed over", "cov_exceeds": "Handed over more than the PO total", "cov_no_total": "No total in the register",
        "memo_po": "Purchase orders", "memo_service": "Services", "partial": "Incomplete month (the latest date in the data is before its end)",
        "attr_auto": "Confirmed branch / Head Office", "attr_review": "Needs review (no explicit branch evidence)", "attr_other": "Unclassified", "branch_unalloc": "Unallocated / needs review", "hq": "Head Office",
        "x_total": "{n} purchase orders ({p} priced) worth {v} EGP, averaging {a} EGP per order, from {s} suppliers.",
        "x_peak": "Highest month by value: {m} ({v} EGP, {n} POs).", "x_conc": "The top {k} suppliers account for {c} of the value; the largest is «{s}» ({sp}).",
        "x_cat": "Highest category by value: «{c}» ({v} EGP, {p}).", "x_req": "{n} requisitions; {w} of them led to a purchase order ({c}).",
        "x_lead": "Median lead time: requisition to PO {a} days; PO to the Finance memo {b} days.",
        "x_memo": "Handover to Finance: {n} memos totalling {v} EGP — {pv} EGP against POs and {sv} EGP for services with no PO.",
        "x_unpriced": "{n} POs have no total in the register: counted as POs, not counted in value (and never treated as zero).",
        "x_canc": "{n} POs are flagged as cancelled, worth {v} EGP included in the total and shown separately here; nothing was removed.",
        "x_canc_nov": "{n} PO(s) flagged as cancelled have no total in the register; nothing was removed.",
        "x_cov": "Per the PO register: {f} POs fully handed over, {p} partly, {z} not at all, {e} handed over more than their total.",
        "x_attr": "{r} of {n} POs have no explicit branch evidence (shown as Unallocated); they are never assigned to a branch by guesswork.",
        "x_partial": "The latest month in the data is incomplete; do not compare it as a full month.",
        "i_basis": "Value = the PO total as stated in the PO register. «Handed to Finance» and «completed and paid» are the register's own words, not a bank-confirmed payment.",
        "i_exclusion": "No status-based exclusion rules are defined yet, so every PO with a total is in the value and cancelled ones are shown separately.",
        "i_filtered": "Filtered view: months by each entity's own date (PO / requisition / memo), supplier on POs, their memos and their requisitions, department on requisitions and their POs.",
        "i_branch": "A branch is assigned only from explicit evidence in the PO text; otherwise Unallocated.",
        "na_payments": "Actual bank payments and dates: there is no payment ledger", "na_lines": "Items, quantities and unit prices: the register is at PO-header level", "na_savings": "Savings and quotation comparison: no quotation data",
        "sev_error": "Error", "sev_warning": "Warning", "sev_info": "Info",
    },
}
CODES = {
    "ar": {"po_branch_not_identified": "أمر شراء بلا فرع محدد", "po_total_missing": "أمر بدون إجمالي", "handover_possible_duplicate": "مذكرة تسليم مكررة محتملة", "handover_exceeds_po_total": "المسلَّم أكبر من إجمالي الأمر",
           "finance_handover_amount_exceeds_total": "مبلغ التسليم في السجل أكبر من الإجمالي", "po_supplier_missing": "أمر بلا مورد", "po_branch_evidence_conflict": "أدلة فرع متعارضة", "supplier_shared_tax_id": "رقم ضريبي مشترك بين موردين",
           "po_requisition_number_differs": "رقم الإشعار يختلف بين الأمر والإشعار", "supplier_duplicate_register_no": "رقم سجل مورد مكرر", "supplier_tax_id_format": "رقم ضريبي بصيغة غير صحيحة", "supplier_tax_id_missing": "مورد بلا رقم ضريبي",
           "supplier_commercial_reg_missing": "مورد بلا سجل تجاري", "requisition_date_missing": "إشعار بلا تاريخ", "po_number_conflict": "رقم أمر متعارض (لم يُحمَّل)", "po_status_indicates_cancellation": "حالة الأمر تدل على الإلغاء",
           "po_handover_without_total": "تسليم للمالية لأمر بلا إجمالي", "po_date_invalid": "تاريخ أمر غير صالح", "handover_po_memo_without_po": "مذكرة أمر شراء بلا رقم أمر", "handover_service_memo_with_po": "مذكرة خدمات مرتبطة بأمر",
           "handover_supplier_unresolved": "مورد المذكرة غير محسوم", "handover_po_not_in_register": "مذكرة لأمر غير موجود في السجل", "branch_shared_email": "بريد فرع مشترك", "branch_missing_email": "فرع بلا بريد",
           "branch_missing_manager": "فرع بلا مدير", "branch_missing_address": "فرع بلا عنوان"},
    "en": {"po_branch_not_identified": "PO without an identified branch", "po_total_missing": "PO without a total", "handover_possible_duplicate": "Possible duplicate handover memo", "handover_exceeds_po_total": "Handed over more than the PO total",
           "finance_handover_amount_exceeds_total": "Register handover amount above the total", "po_supplier_missing": "PO without a supplier", "po_branch_evidence_conflict": "Conflicting branch evidence", "supplier_shared_tax_id": "Tax ID shared by suppliers",
           "po_requisition_number_differs": "Requisition number differs between PO and requisition", "supplier_duplicate_register_no": "Duplicate supplier register number", "supplier_tax_id_format": "Tax ID in the wrong format", "supplier_tax_id_missing": "Supplier without a tax ID",
           "supplier_commercial_reg_missing": "Supplier without a commercial register", "requisition_date_missing": "Requisition without a date", "po_number_conflict": "Conflicting PO number (not loaded)", "po_status_indicates_cancellation": "PO status indicates cancellation",
           "po_handover_without_total": "Handover for a PO without a total", "po_date_invalid": "Invalid PO date", "handover_po_memo_without_po": "PO memo without a PO number", "handover_service_memo_with_po": "Service memo linked to a PO",
           "handover_supplier_unresolved": "Memo supplier unresolved", "handover_po_not_in_register": "Memo for a PO not in the register", "branch_shared_email": "Branch e-mail shared", "branch_missing_email": "Branch without e-mail",
           "branch_missing_manager": "Branch without a manager", "branch_missing_address": "Branch without an address"},
}


class C:
    def __init__(self, lang):
        self.lang, self.s = lang, T[lang]

    def t(self, key, **kw):
        return self.s[key].format(**kw) if kw else self.s[key]

    def name(self, k, empty="unspec"):
        return k if k else self.t(empty)


def _m(lang, m, short=False):
    return period_label(lang, m, short)


def build_report(a: dict, batches: list[dict], exceptions: list[dict], th: dict, th_origin: dict, lang: str, filters: dict, dims: list[dict], files: list[str]) -> ReportModel:
    c = C(lang)
    t = a["totals"]
    months = a["months"]
    rm = ReportModel(title=c.t("title"), period_label=(f"{_m(lang, months[0]['period'])} – {_m(lang, months[-1]['period'])}" if months else ""), sections=[], lang=lang)
    rm.subtitle = f"{c.t('source')}: " + " · ".join(files[:4]) + (" · " + c.t("filtered") if a["filtered"] else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(files[:3]), "file_hash": "", "filters": {"active": filters, "options": {}, "dimensions": dims}}
    pl = a["pipeline"]

    # ---------------------------------------------------------------- summary
    items = [{"metric": "total", "text": c.t("x_total", n=t["po_n"], p=t["priced_n"], v=money2(t["spend"]), a=money2(t["avg_po"]) if t["avg_po"] is not None else "—", s=t["suppliers_n"])}]
    if months:
        pk = max(months, key=lambda m: m["po_value"])
        items.append({"metric": "peak", "text": c.t("x_peak", m=_m(lang, pk["period"]), v=money2(pk["po_value"]), n=pk["po_n"])})
    named = [s for s in a["suppliers"] if s["key"]]
    if named:
        items.append({"metric": "conc", "text": c.t("x_conc", k=th["concentration_top_n"], c=pct(a["concentration_pct"]), s=named[0]["key"], sp=pct(named[0]["share"]))})
    if a["categories"]:
        top = next((x for x in a["categories"] if x["key"]), None)
        if top:
            items.append({"metric": "cat", "text": c.t("x_cat", c=top["key"], v=money2(top["value"]), p=pct(top["share"]))})
    if t["req_n"]:
        items.append({"metric": "req", "text": c.t("x_req", n=t["req_n"], w=t["req_with_po_n"], c=pct(t["req_conversion_pct"]))})
    if pl["req_to_po_days"]["median"] is not None or pl["po_to_memo_days"]["median"] is not None:
        fm = lambda x: "—" if x is None else f"{x:g}"
        items.append({"metric": "lead", "text": c.t("x_lead", a=fm(pl["req_to_po_days"]["median"]), b=fm(pl["po_to_memo_days"]["median"]))})
    if t["memo_n"]:
        items.append({"metric": "memo", "text": c.t("x_memo", n=t["memo_n"], v=money2(t["memo_amount"]), pv=money2(t["memo_po_amount"]), sv=money2(t["memo_service_amount"]))})
    cv = pl["coverage"]
    items.append({"metric": "cov", "text": c.t("x_cov", f=cv["full"], p=cv["partial"], z=cv["none"], e=cv["exceeds"])})
    if t["unpriced_n"]:
        items.append({"metric": "unpriced", "text": c.t("x_unpriced", n=t["unpriced_n"])})
    if t["cancelled_n"]:
        items.append({"metric": "canc", "text": c.t("x_canc", n=t["cancelled_n"], v=money2(t["cancelled_value"])) if t["cancelled_value"] else c.t("x_canc_nov", n=t["cancelled_n"])})
    review = a["attribution"]["review"]
    if review:
        items.append({"metric": "attr", "text": c.t("x_attr", r=review, n=t["po_n"])})
    if months and months[-1]["partial"]:
        items.append({"metric": "partial", "text": c.t("x_partial")})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = [{"label": c.t("k_po"), "value": f"{t['po_n']:,}", "sub": f"{t['priced_n']} / {t['po_n']}"}, {"label": c.t("k_value"), "value": money2(t["spend"]), "sub": c.t("egp")},
                {"label": c.t("k_avg"), "value": money2(t["avg_po"]) if t["avg_po"] is not None else "—", "sub": c.t("egp")}, {"label": c.t("k_sup"), "value": str(t["suppliers_n"]), "sub": ""},
                {"label": c.t("k_canc"), "value": str(t["cancelled_n"]), "sub": money2(t["cancelled_value"]) + " " + c.t("egp")}, {"label": c.t("k_req"), "value": f"{t['req_n']:,}", "sub": ""},
                {"label": c.t("k_conv"), "value": pct(t["req_conversion_pct"]), "sub": f"{t['req_with_po_n']} / {t['req_n']}"},
                {"label": c.t("k_memo"), "value": money2(t["memo_amount"]), "sub": f"{t['memo_n']} · {c.t('egp')}"},
                {"label": c.t("k_memo_po"), "value": money2(t["memo_po_amount"]), "sub": f"{t['memo_po_n']} · {c.t('egp')}"}, {"label": c.t("k_memo_svc"), "value": money2(t["memo_service_amount"]), "sub": f"{t['memo_service_n']} · {c.t('egp')}"},
                {"label": c.t("k_handed"), "value": money2(t["handed_register"]), "sub": c.t("egp")}, {"label": c.t("k_rem"), "value": money2(t["remaining_register"]), "sub": c.t("egp")}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights += [{"severity": "info", "text": c.t("i_basis")}, {"severity": "info", "text": c.t("i_exclusion")}]
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- monthly
    sec = ReportSection(c.t("s_monthly"), "monthly")
    if months:
        x = [_m(lang, m["period"], True) for m in months]
        sec.charts.append({"type": "bar", "title": c.t("ch_month"), "x": x, "series": [{"name": c.t("c_value"), "values": [float(m["po_value"]) for m in months]}]})
        sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [
            col("period", c.t("c_month")), col("po", c.t("c_po"), "int"), col("value", c.t("c_value"), "money"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct"),
            col("req", c.t("c_req"), "int"), col("mpo", c.t("c_memo_po"), "money"), col("msvc", c.t("c_memo_svc"), "money"), col("note", c.t("c_note"))],
            "rows": [{"period": _m(lang, m["period"]), "po": m["po_n"], "value": m["po_value"], "d": m.get("d_value"), "dp": m.get("d_value_pct"), "req": m["req_n"],
                      "mpo": m["memo_po"], "msvc": m["memo_svc"], "note": c.t("partial") if m["partial"] else ""} for m in months]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- suppliers
    sec = ReportSection(c.t("s_suppliers"), "suppliers")
    top = a["suppliers"][: int(th["top_n"])]
    sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_sup"), "x": [c.name(s["key"], "no_supplier") for s in top], "series": [{"name": c.t("c_value"), "values": [float(s["value"]) for s in top]}]}) if top else None
    sec.charts = [z for z in sec.charts if z]
    sec.tables.append({"key": "suppliers", "title": c.t("t_sup"), "columns": [col("rank", c.t("c_rank"), "int"), col("supplier", c.t("c_supplier")), col("n", c.t("c_po"), "int"), col("value", c.t("c_value"), "money"),
                                                                                col("share", c.t("c_share"), "pct"), col("cum", c.t("c_cum"), "pct"), col("avg", c.t("c_avg"), "money")],
                       "rows": [{"rank": i, "supplier": c.name(s["key"], "no_supplier"), "n": s["n"], "value": s["value"], "share": s["share"], "cum": s["cum_share"], "avg": s["avg"]} for i, s in enumerate(a["suppliers"], 1)], "pdf_rows": 30})
    sec.tables.append({"key": "supplier_categories", "title": c.t("t_supcat"), "columns": [col("cat", c.t("c_cat")), col("n", c.t("c_po"), "int"), col("value", c.t("c_value"), "money"), col("share", c.t("c_share"), "pct")],
                       "rows": [{"cat": c.name(s["key"], "no_cat"), "n": s["n"], "value": s["value"], "share": s["share"]} for s in a["supplier_categories"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- categories
    sec = ReportSection(c.t("s_categories"), "categories")
    cats = a["categories"]
    if cats:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_cat"), "x": [c.name(s["key"], "no_cat") for s in cats[:10]], "series": [{"name": c.t("c_value"), "values": [float(s["value"]) for s in cats[:10]]}]})
    sec.tables.append({"key": "categories", "title": c.t("t_cat"), "columns": [col("cat", c.t("c_cat")), col("n", c.t("c_po"), "int"), col("value", c.t("c_value"), "money"), col("share", c.t("c_share"), "pct"), col("avg", c.t("c_avg"), "money")],
                       "rows": [{"cat": c.name(s["key"], "no_cat"), "n": s["n"], "value": s["value"], "share": s["share"], "avg": s["avg"]} for s in cats]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- departments / flow
    sec = ReportSection(c.t("s_departments"), "departments")
    sec.tables.append({"key": "departments", "title": c.t("t_dept"), "columns": [col("dept", c.t("c_dept")), col("req", c.t("c_req"), "int"), col("urgent", c.t("c_urgent"), "int"), col("withpo", c.t("c_withpo"), "int"),
                                                                                  col("conv", c.t("c_conv"), "pct"), col("po", c.t("c_po"), "int"), col("value", c.t("c_value"), "money")],
                       "rows": [{"dept": c.name(d["key"]), "req": d["req_n"], "urgent": d["urgent_n"], "withpo": d["with_po_n"], "conv": d["conversion"], "po": d["po_n"], "value": d["po_value"]} for d in a["departments"]]})
    for key, title, rows in (("req_status", "t_reqstatus", a["req_status"]), ("priority", "t_prio", a["priority"])):
        sec.tables.append({"key": key, "title": c.t(title), "columns": [col("k", c.t("c_status")), col("n", c.t("c_n"), "int")], "rows": [{"k": c.name(r["key"]), "n": r["n"]} for r in rows]})
    sec.tables.append({"key": "po_status", "title": c.t("t_postatus"), "columns": [col("k", c.t("c_status")), col("n", c.t("c_po"), "int"), col("v", c.t("c_value"), "money")],
                       "rows": [{"k": c.name(r["key"]), "n": r["n"], "v": r["value"]} for r in a["po_status"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- finance and lead times
    sec = ReportSection(c.t("s_finance"), "finance")
    sec.tables.append({"key": "lead", "title": c.t("t_lead"), "columns": [col("k", c.t("c_key")), col("n", c.t("c_pairs"), "int"), col("med", c.t("c_median"), "num"), col("p90", c.t("c_p90"), "num"),
                                                                         col("neg", c.t("c_neg"), "int"), col("long", c.t("c_long"), "int")],
                       "rows": [{"k": c.t("lead_req"), "n": pl["req_to_po_days"]["n"], "med": pl["req_to_po_days"]["median"], "p90": pl["req_to_po_days"]["p90"], "neg": pl["req_to_po_days"]["negative"], "long": pl["req_to_po_days"]["long"]},
                                {"k": c.t("lead_memo"), "n": pl["po_to_memo_days"]["n"], "med": pl["po_to_memo_days"]["median"], "p90": pl["po_to_memo_days"]["p90"], "neg": pl["po_to_memo_days"]["negative"], "long": pl["po_to_memo_days"]["long"]}]})
    sec.tables.append({"key": "coverage", "title": c.t("t_cov"), "columns": [col("k", c.t("c_cov")), col("n", c.t("c_po"), "int")], "rows": [{"k": c.t("cov_" + k), "n": cv[k]} for k in ("full", "partial", "none", "exceeds", "no_total")]})
    sec.tables.append({"key": "memo_categories", "title": c.t("t_memocat"), "columns": [col("type", c.t("c_type")), col("cat", c.t("c_cat")), col("n", c.t("c_n"), "int"), col("amount", c.t("c_amount"), "money")],
                       "rows": [{"type": c.t("memo_" + m["type"]), "cat": c.name(m["key"], "no_cat"), "n": m["n"], "amount": m["amount"]} for m in a["memo_categories"]], "pdf_rows": 30})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- quality
    sec = ReportSection(c.t("s_quality"), "quality")
    sec.insights.append({"severity": "info", "text": c.t("i_branch")})
    sec.insights.append({"severity": "info", "text": c.t("t_na") + ":"})
    sec.insights += [{"severity": "info", "text": c.t("na_" + k)} for k in ("payments", "lines", "savings")]
    at = a["attribution"]
    sec.tables.append({"key": "attribution", "title": c.t("t_attr"), "columns": [col("k", c.t("c_status")), col("n", c.t("c_po"), "int")],
                       "rows": [{"k": c.t("attr_auto"), "n": at["auto"]}, {"k": c.t("attr_review"), "n": at["review"]}, {"k": c.t("attr_other"), "n": at["other"]}]})
    sec.tables.append({"key": "branch_value", "title": c.t("t_bval"), "columns": [col("k", c.t("c_branch")), col("n", c.t("c_po"), "int"), col("v", c.t("c_value"), "money")],
                       "rows": [{"k": (c.t("hq") if b["key"] == "HQ" else b["key"]) if b["key"] else c.t("branch_unalloc"), "n": b["n"], "v": b["value"]} for b in a["branch_value"]], "pdf_rows": 25})
    sec.tables.append({"key": "batches", "title": c.t("t_batches"), "columns": [col("m", c.t("c_key")), col("sheet", c.t("c_file")), col("rows", c.t("c_rows"), "int"), col("loaded", c.t("c_loaded"), "int"), col("held", c.t("c_held"), "int"), col("status", c.t("c_status"))],
                       "rows": [{"m": b["module"], "sheet": b["sheet"] or b["file"], "rows": b["rows"], "loaded": b["loaded"], "held": b["held"], "status": b["status"]} for b in batches]})
    from app.modules.procurement_analysis.engine import exception_summary
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [col("msg", c.t("c_issue")), col("sev", c.t("c_sev")), col("n", c.t("c_n"), "int"), col("ex", c.t("c_examples"))],
                       "rows": [{"msg": CODES[lang].get(e["code"], e["code"]), "sev": c.t("sev_" + e["severity"]) if ("sev_" + e["severity"]) in c.s else e["severity"], "n": e["n"], "ex": " | ".join(e["examples"])} for e in exception_summary(exceptions)], "pdf_rows": 30})
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_val")), col("o", c.t("c_origin"))], "rows": [{"n": k, "v": th[k], "o": th_origin[k]} for k in th]})
    rm.sections.append(sec)
    return rm


_ = (Decimal, smoney, spct)
