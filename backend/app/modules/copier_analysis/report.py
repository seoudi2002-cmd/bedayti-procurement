"""ReportModel for the copier module: one cycle (a month) or the multi-month trend. Every sentence of the executive
summary is generated from computed metrics; nothing is stated that the sources do not support."""
from datetime import datetime, timezone
from decimal import Decimal

from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money, money2, pct, period_label, smoney, spct

CLASS_FMT = {
    "ar": {"mono_copier": "ماكينات {n} نسخة", "printer": "طابعات {n} نسخة", "color_copier": "ماكينات ألوان {n} نسخة", "color_a3": "ألوان A3 زيروكس {n} نسخة"},
    "en": {"mono_copier": "Copiers {n} pages", "printer": "Printers {n} pages", "color_copier": "Colour copiers {n} pages", "color_a3": "Colour A3 Xerox {n} pages"},
}

T = {
    "ar": {
        "title": "تحليل ماكينات التصوير والطباعة", "title_trend": "تحليل ماكينات التصوير والطباعة — الاتجاه الشهري", "source": "المصادر", "period": "الفترة",
        "s_summary": "الملخص التنفيذي", "s_fleet": "الأسطول والباقات", "s_usage": "الاستهلاك والاستخدام", "s_cost": "التكلفة",
        "s_loc": "المحافظات والفروع", "s_recon": "مطابقة الكشف مع الفاتورة", "s_trend": "الاتجاه الشهري", "s_evidence": "الأدلة المساندة (للتحقق فقط)",
        "s_quality": "جودة البيانات وحدود التحليل",
        "k_machines": "عدد الماكينات", "k_cons": "إجمالي الاستهلاك", "k_allow": "النسخ المشمولة بالباقات", "k_util": "نسبة الاستخدام",
        "k_exc": "النسخ الإضافية", "k_inexc": "ماكينات تجاوزت باقتها", "k_rent": "الإيجار (قبل الضريبة)", "k_exccost": "تكلفة النسخ الإضافية",
        "k_cost": "إجمالي التكلفة (قبل الضريبة)", "k_cpp": "تكلفة النسخة الفعلية", "k_inv": "إجمالي الفاتورة (بعد الضرائب)", "k_recon": "مطابقة الفاتورة",
        "k_under": "ماكينات قليلة الاستخدام", "k_unused": "نسخ مشمولة غير مستخدمة", "egp": "ج.م", "pages": "نسخة",
        "recon_ok": "كل البنود مطابقة", "recon_diff": "{n} بند فيه فرق", "recon_none": "لا توجد فاتورة",
        "c_class": "الفئة", "c_machines": "ماكينات", "c_package": "الباقة", "c_allow": "المشمول", "c_cons": "الاستهلاك", "c_util": "الاستخدام %",
        "c_exc": "نسخ إضافية", "c_inexc": "ماكينات متجاوزة", "c_rentu": "إيجار الماكينة", "c_rent": "الإيجار", "c_excr": "سعر النسخة الإضافية",
        "c_exccost": "تكلفة الإضافي", "c_cost": "التكلفة", "c_cpp": "تكلفة النسخة", "c_branch": "الفرع", "c_loc": "المحافظة / القسم", "c_rank": "الترتيب",
        "c_share": "النسبة %", "c_excpct": "الإضافي % من الباقة", "c_unused": "غير المستخدم", "c_check": "المطابقة", "c_subject": "البند",
        "c_expected": "حسب الكشف", "c_invoiced": "حسب الفاتورة", "c_diff": "الفرق", "c_status": "الحالة", "c_ref": "المرجع", "c_issue": "الملاحظة",
        "c_sev": "الأهمية", "c_count": "العدد", "c_examples": "أمثلة", "c_key": "البيان", "c_val": "القيمة", "c_page": "الصفحة", "c_counter": "العداد",
        "c_printed": "تاريخ الطباعة", "c_machine": "الماكينة المطابقة", "c_note": "ملاحظة", "c_src": "المصدر", "c_name": "الإعداد", "c_source": "المصدر",
        "c_period": "الفترة", "c_mom": "التغير", "c_mompct": "التغير %", "c_invtotal": "إجمالي الفاتورة", "c_recon": "المطابقة", "c_class2": "الفئة",
        "t_class": "الأسطول حسب الفئة", "t_bands": "توزيع نسبة الاستخدام", "t_under": "ماكينات قليلة الاستخدام", "t_exceed": "ماكينات تجاوزت باقتها",
        "t_top": "الأعلى استهلاكًا", "t_loc": "المقارنة بين المحافظات والأقسام", "t_branch": "ترتيب الفروع", "t_recon": "مطابقة الكشف (الجزء 1) مع الفاتورة",
        "t_support": "مطابقة مساندة (الجزء 2 / الفاتورة)", "t_internal": "اتساق حسابات الفاتورة نفسها", "t_inv": "بيانات الفاتورة", "t_issues": "ملاحظات جودة البيانات",
        "t_sources": "الملفات المرفوعة لهذه الفترة", "t_settings": "الإعدادات المستخدمة", "t_trend": "المؤشرات حسب الشهر", "t_cont": "استمرارية القراءات بين الشهور",
        "t_evid": "صفحات الحالة الممسوحة", "ch_class": "الاستهلاك مقابل المشمول حسب الفئة", "ch_bands": "عدد الماكينات حسب نسبة الاستخدام",
        "ch_top": "أعلى الفروع استهلاكًا", "ch_loc": "الاستهلاك حسب المحافظة / القسم", "ch_cost": "تركيب التكلفة حسب الفئة (قبل الضريبة)",
        "ch_exc": "النسخ الإضافية حسب الفئة", "ch_tcons": "الاستهلاك والمشمول شهريًا", "ch_tcost": "التكلفة قبل الضريبة شهريًا",
        "b_almost": "شبه غير مستخدمة", "b_low": "قليلة الاستخدام", "b_mid": "استخدام متوسط", "b_high": "ضمن الباقة (50–100%)", "b_over": "تجاوزت الباقة",
        "st_ok": "مطابق", "st_diff": "فرق", "st_na": "غير قابل للمطابقة", "sev_critical": "حرج", "sev_warning": "تنبيه", "sev_info": "للعلم",
        "unsupported_head": "غير مدعوم بالمصادر المرفوعة (لم تُحسب أرقام بديلة):", "un_cost": "التكلفة (تحتاج فاتورة المورد)",
        "un_invoice_reconciliation": "مطابقة الفاتورة (لا توجد فاتورة)", "un_location": "المقارنة حسب المحافظة (لا يوجد الجزء 2 / ملف Word)",
        "un_trend": "الاتجاه الشهري (فترة واحدة فقط)",
        "rk_rent_qty": "عدد الماكينات المؤجرة", "rk_rent_amount": "قيمة الإيجار", "rk_rent_unit": "سعر إيجار الماكينة (الجزء 2 مقابل الفاتورة)",
        "rk_excess_qty": "النسخ الإضافية", "rk_excess_amount": "قيمة النسخ الإضافية", "rk_line_arith": "الكمية × السعر = إجمالي البند",
        "rk_total_expected_sales": "إجمالي المبيعات", "rk_total_line_sum": "مجموع البنود = إجمالي الفاتورة", "rk_total_vat": "ضريبة القيمة المضافة",
        "rk_total_wht": "الخصم تحت حساب الضريبة", "rk_total_grand": "المبلغ الإجمالي", "rk_line_kind": "بند غير مصنف",
        "i_head": "الفاتورة", "iv_internal": "الرقم الداخلي", "iv_electronic": "الرقم الإلكتروني", "iv_issued": "تاريخ الإصدار", "iv_status": "الحالة",
        "iv_seller": "البائع", "iv_buyer": "المشتري", "iv_sales": "إجمالي المبيعات", "iv_vat": "ضريبة القيمة المضافة", "iv_wht": "الخصم تحت حساب الضريبة",
        "iv_grand": "المبلغ الإجمالي", "iv_lines": "عدد البنود",
        "e_note": "هذه الصفحات أدلة مساندة للتحقق فقط. لا تدخل في أي مؤشر أو تكلفة أو إجمالي؛ وعند أي تعارض يُعتمد الكشف والفاتورة.",
        "evn_no_match": "لا ماكينة في الكشف لها هذه القراءة (قراءة خاطئة للعداد أو تعارض: تُراجع)", "evn_duplicate": "نفس عداد صفحة أخرى",
        "evn_ambiguous": "أكثر من ماكينة لها هذه القراءة", "evn_unreadable": "لم يُقرأ عداد في الصفحة",
        "ev_matched": "مطابقة لقراءة في الكشف", "ev_no_match": "لا تطابق أي قراءة (مراجعة)", "ev_unreadable": "لا يمكن قراءة العداد", "ev_duplicate": "صفحة مكررة",
        "ev_ambiguous": "قراءة مشتركة بين ماكينات", "ev_processing": "جاري معالجة الصفحات…", "ev_failed": "تعذرت قراءة الملف",
        "x_fleet": "تضم الدورة {n} ماكينة في {k} فئة؛ أكبرها «{c}» ({cn} ماكينة).",
        "x_use": "بلغ الاستهلاك {cons} نسخة مقابل {allow} نسخة مشمولة بالباقات (استخدام {util})؛ ولم يُستخدم {unused} نسخة مشمولة ({upct}).",
        "x_exc": "تجاوزت {n} ماكينة ({np}) باقتها بإجمالي {exc} نسخة إضافية{cost}.",
        "x_exc_cost": " بتكلفة {cost} ج.م قبل الضريبة (حسب أسعار الفاتورة)",
        "x_cost": "التكلفة قبل الضريبة {cost} ج.م (إيجار {rent} + نسخ إضافية {exc})، بمتوسط {cpp} ج.م للنسخة.",
        "x_loc": "أعلى محافظة أو قسم استهلاكًا «{n}» ({cons} نسخة، {share} من الإجمالي).",
        "x_branch": "أعلى فرع استهلاكًا «{n}» ({cons} نسخة)؛ وأعلى فرع في النسخ الإضافية «{e}» ({exc} نسخة).",
        "x_under": "{n} ماكينة استخدامها أقل من {t}% من باقتها، منها {v} شبه غير مستخدمة (أقل من {vt}%).",
        "x_recon_ok": "مطابقة الكشف مع الفاتورة: كل البنود الأساسية ({n}) متطابقة، وإجمالي المبيعات {sales} ج.م يساوي المحسوب من الكشف بأسعار الفاتورة.",
        "x_recon_diff": "مطابقة الكشف مع الفاتورة: {d} من {n} بند أساسي فيه فرق (انظر قسم المطابقة).",
        "x_recon_none": "لا توجد فاتورة مرفوعة لهذه الفترة؛ التكلفة والمطابقة غير محسوبتين.",
        "x_trend": "تغير الاستهلاك بين {a} و{b}: {d} ({p}).",
        "i_cost_note": "التكلفة موزعة من أسعار الفاتورة نفسها (إيجار كل فئة + النسخ الإضافية × سعر فئتها) وقبل الضريبة؛ ضريبة الفاتورة والخصم لا تُوزع على الماكينات.",
        "i_loc_note": "المحافظة/القسم مأخوذة من الجزء 2 من الكشف ومن ملف Word (مساندان)، وليست من الجزء 1.",
        "i_loc_missing": "{n} ماكينة بلا محافظة في الجزء 2/Word (تظهر «—»).",
        "i_evidence": "تغطية الأدلة: {m} صفحة مطابقة من {t} صفحة ممسوحة (للتحقق فقط).",
        "i_filtered": "العرض الحالي مفلتر؛ مطابقة الفاتورة تخص الدورة كلها ولا تُعرض مع الفلاتر.",
        "i_thr": "حدود الاستخدام القليل والتجاوز هي القيم الابتدائية ولم تُعتمد بعد؛ يمكن تعديلها من إعدادات النظام.",
        "i_single": "المصادر تغطي فترة واحدة؛ الاتجاه الشهري يتطلب رفع كشوف شهور أخرى.",
        "f_governorates": "المحافظة / القسم", "f_branches": "الفرع", "f_classes": "الفئة", "f_filtered": "عرض مفلتر", "other": "أخرى",
        "tr_machines": "الماكينات", "tr_cons": "الاستهلاك", "tr_allow": "المشمول", "tr_util": "الاستخدام %", "tr_exc": "نسخ إضافية", "tr_rent": "الإيجار",
        "tr_exccost": "تكلفة الإضافي", "tr_cost": "التكلفة قبل الضريبة", "tr_inv": "إجمالي الفاتورة",
        "cont_note": "القراءة السابقة لكل ماكينة يجب أن تساوي القراءة الحالية في الشهر السابق؛ غير ذلك يعني فجوة أو تغيير ماكينة أو فرعًا غير مطابق.",
    },
    "en": {
        "title": "Copier & Printing-machine Analytics", "title_trend": "Copier & Printing-machine Analytics — monthly trend", "source": "Sources", "period": "Period",
        "s_summary": "Executive summary", "s_fleet": "Fleet and packages", "s_usage": "Consumption and utilisation", "s_cost": "Cost",
        "s_loc": "Governorates and branches", "s_recon": "Statement vs invoice reconciliation", "s_trend": "Monthly trend", "s_evidence": "Supporting evidence (validation only)",
        "s_quality": "Data quality and analysis limits",
        "k_machines": "Machines", "k_cons": "Total consumption", "k_allow": "Copies included in packages", "k_util": "Utilisation",
        "k_exc": "Additional copies", "k_inexc": "Machines over their package", "k_rent": "Rent (pre-tax)", "k_exccost": "Additional-copy cost",
        "k_cost": "Total cost (pre-tax)", "k_cpp": "Effective cost per copy", "k_inv": "Invoice total (incl. taxes)", "k_recon": "Invoice reconciliation",
        "k_under": "Under-utilised machines", "k_unused": "Included copies not used", "egp": "EGP", "pages": "copies",
        "recon_ok": "All lines match", "recon_diff": "{n} lines differ", "recon_none": "No invoice",
        "c_class": "Class", "c_machines": "Machines", "c_package": "Package", "c_allow": "Included", "c_cons": "Consumption", "c_util": "Utilisation %",
        "c_exc": "Additional copies", "c_inexc": "Machines over", "c_rentu": "Rent per machine", "c_rent": "Rent", "c_excr": "Additional-copy rate",
        "c_exccost": "Additional cost", "c_cost": "Cost", "c_cpp": "Cost per copy", "c_branch": "Branch", "c_loc": "Governorate / section", "c_rank": "Rank",
        "c_share": "Share %", "c_excpct": "Additional % of package", "c_unused": "Unused", "c_check": "Check", "c_subject": "Line",
        "c_expected": "Per statement", "c_invoiced": "Per invoice", "c_diff": "Difference", "c_status": "Status", "c_ref": "Reference", "c_issue": "Observation",
        "c_sev": "Severity", "c_count": "Count", "c_examples": "Examples", "c_key": "Item", "c_val": "Value", "c_page": "Page", "c_counter": "Counter",
        "c_printed": "Printed at", "c_machine": "Matched machine", "c_note": "Note", "c_src": "Source", "c_name": "Setting", "c_source": "Source",
        "c_period": "Period", "c_mom": "Change", "c_mompct": "Change %", "c_invtotal": "Invoice total", "c_recon": "Reconciliation", "c_class2": "Class",
        "t_class": "Fleet by class", "t_bands": "Utilisation distribution", "t_under": "Under-utilised machines", "t_exceed": "Machines over their package",
        "t_top": "Highest consumption", "t_loc": "Governorate / section comparison", "t_branch": "Branch ranking", "t_recon": "Statement (Part 1) vs invoice",
        "t_support": "Supporting checks (Part 2 / invoice)", "t_internal": "Invoice internal consistency", "t_inv": "Invoice details", "t_issues": "Data-quality observations",
        "t_sources": "Files uploaded for this period", "t_settings": "Settings used", "t_trend": "Indicators by month", "t_cont": "Reading continuity between months",
        "t_evid": "Scanned status pages",
        "ch_class": "Consumption vs included, by class", "ch_bands": "Machines by utilisation band", "ch_top": "Top branches by consumption",
        "ch_loc": "Consumption by governorate / section", "ch_cost": "Cost composition by class (pre-tax)", "ch_exc": "Additional copies by class",
        "ch_tcons": "Consumption and included copies by month", "ch_tcost": "Pre-tax cost by month",
        "b_almost": "Almost unused", "b_low": "Under-utilised", "b_mid": "Medium use", "b_high": "Within package (50–100%)", "b_over": "Over package",
        "st_ok": "Matches", "st_diff": "Differs", "st_na": "Not comparable", "sev_critical": "Critical", "sev_warning": "Warning", "sev_info": "Info",
        "unsupported_head": "Not supported by the uploaded sources (no substitute figures were calculated):", "un_cost": "Cost (needs the supplier invoice)",
        "un_invoice_reconciliation": "Invoice reconciliation (no invoice)", "un_location": "Governorate comparison (no Part 2 / Word file)",
        "un_trend": "Monthly trend (one period only)",
        "rk_rent_qty": "Rented machines", "rk_rent_amount": "Rent amount", "rk_rent_unit": "Rent per machine (Part 2 vs invoice)",
        "rk_excess_qty": "Additional copies", "rk_excess_amount": "Additional-copy amount", "rk_line_arith": "Quantity × price = line total",
        "rk_total_expected_sales": "Total sales", "rk_total_line_sum": "Σ lines = invoice total", "rk_total_vat": "VAT",
        "rk_total_wht": "Withholding on account", "rk_total_grand": "Grand total", "rk_line_kind": "Unclassified line",
        "i_head": "Invoice", "iv_internal": "Internal number", "iv_electronic": "Electronic number", "iv_issued": "Issue date", "iv_status": "Status",
        "iv_seller": "Seller", "iv_buyer": "Buyer", "iv_sales": "Total sales", "iv_vat": "VAT", "iv_wht": "Withholding on account",
        "iv_grand": "Grand total", "iv_lines": "Lines",
        "e_note": "These pages are supporting evidence for validation only. They feed no KPI, cost or total; on any conflict the statement and the invoice prevail.",
        "evn_no_match": "No machine in the statement has this reading (misread counter or a conflict: review)", "evn_duplicate": "Same counter as another page",
        "evn_ambiguous": "More than one machine has this reading", "evn_unreadable": "No counter could be read on the page",
        "ev_matched": "Matches a statement reading", "ev_no_match": "No reading matches (review)", "ev_unreadable": "Counter not readable", "ev_duplicate": "Duplicate page",
        "ev_ambiguous": "Reading shared by machines", "ev_processing": "Processing pages…", "ev_failed": "The file could not be read",
        "x_fleet": "The period has {n} machines in {k} classes; the largest is “{c}” ({cn} machines).",
        "x_use": "Consumption was {cons} copies against {allow} included in the packages ({util} utilisation); {unused} included copies ({upct}) were not used.",
        "x_exc": "{n} machines ({np}) exceeded their package, for {exc} additional copies{cost}.",
        "x_exc_cost": " costing EGP {cost} before tax (at the invoice's rates)",
        "x_cost": "Pre-tax cost is EGP {cost} (rent {rent} + additional copies {exc}), an average of EGP {cpp} per copy.",
        "x_loc": "The highest-consumption governorate/section is “{n}” ({cons} copies, {share} of the total).",
        "x_branch": "The highest-consumption branch is “{n}” ({cons} copies); the highest in additional copies is “{e}” ({exc} copies).",
        "x_under": "{n} machines use less than {t}% of their package, {v} of them almost unused (below {vt}%).",
        "x_recon_ok": "Statement vs invoice: all {n} primary checks match, and total sales of EGP {sales} equal the statement's quantities at the invoice's unit prices.",
        "x_recon_diff": "Statement vs invoice: {d} of {n} primary checks differ (see the reconciliation section).",
        "x_recon_none": "No invoice is uploaded for this period; cost and reconciliation are not calculated.",
        "x_trend": "Consumption between {a} and {b}: {d} ({p}).",
        "i_cost_note": "Costs are allocated from the invoice's own prices (class rent + additional copies × the class rate) and are pre-tax; the invoice's VAT and withholding are not spread over machines.",
        "i_loc_note": "Governorate/section comes from Part 2 of the statement and the Word file (supporting sources), not from Part 1.",
        "i_loc_missing": "{n} machines have no governorate in Part 2/Word (shown as “—”).",
        "i_evidence": "Evidence coverage: {m} of {t} scanned pages match a statement reading (validation only).",
        "i_filtered": "This view is filtered; invoice reconciliation covers the whole period and is not shown with filters.",
        "i_thr": "Under-utilisation and over-package thresholds are still the initial values and not yet confirmed; adjust them in system settings.",
        "i_single": "The sources cover one period; a monthly trend needs other months' statements.",
        "f_governorates": "Governorate / section", "f_branches": "Branch", "f_classes": "Class", "f_filtered": "Filtered view", "other": "Other",
        "tr_machines": "Machines", "tr_cons": "Consumption", "tr_allow": "Included", "tr_util": "Utilisation %", "tr_exc": "Additional copies", "tr_rent": "Rent",
        "tr_exccost": "Additional cost", "tr_cost": "Pre-tax cost", "tr_inv": "Invoice total",
        "cont_note": "A machine's previous reading should equal last month's current reading; otherwise there is a gap, a replaced machine or a branch that does not match.",
    },
}


class C:
    def __init__(self, lang: str):
        self.lang, self.s = lang, T[lang]

    def t(self, key: str, **kw) -> str:
        return self.s[key].format(**kw) if kw else self.s[key]

    def cls(self, key: str) -> str:
        fam, _, n = key.rpartition("_")
        return CLASS_FMT[self.lang].get(fam, key).format(n=n) if fam else key


def _meta(c: C, rm: ReportModel, cycle: dict, filters: dict, dims: list[dict]) -> None:
    rm.meta = {"cycle_id": cycle["id"], "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "period": cycle.get("period"),
               "file_name": ", ".join(s["file_name"] for s in cycle.get("sources", [])[:3]), "file_hash": "",
               "filters": {"active": filters, "options": {}, "dimensions": dims}}


def build_cycle_report(cycle: dict, a: dict, invoice: dict | None, evidence: dict | None, issues: list[dict], th: dict, th_origin: dict,
                       lang: str = "ar", filters: dict | None = None, dims: list[dict] | None = None, support: dict | None = None) -> ReportModel:
    c = C(lang)
    filters = {k: v for k, v in (filters or {}).items() if v}
    per = tuple(cycle["period"])
    rm = ReportModel(title=c.t("title"), period_label=period_label(lang, per), sections=[], lang=lang)
    rm.subtitle = f"{c.t('source')}: " + " · ".join(f"{s['file_name']}" for s in cycle["sources"])
    _meta(c, rm, cycle, filters, dims or [])
    if filters:
        rm.subtitle += " · " + c.t("f_filtered")
    tot = a["totals"]
    rec = a.get("reconciliation")
    caveats: list[str] = []
    if filters:
        caveats.append(c.t("i_filtered"))
    if a["has_invoice"]:
        caveats.append(c.t("i_cost_note"))
    if a["by_location"]:
        caveats.append(c.t("i_loc_note"))
        if a["unassigned_location"]:
            caveats.append(c.t("i_loc_missing", n=a["unassigned_location"]))
    caveats.append(c.t("i_single"))
    if evidence and evidence["status"] == "ready":
        pg = evidence["pages"]
        caveats.append(c.t("i_evidence", m=sum(1 for p in pg if p["status"] == "matched"), t=len(pg)))
    if all(v == "default" for v in th_origin.values()):
        caveats.append(c.t("i_thr"))
    for u in a["unsupported"]:
        caveats.append(c.t("unsupported_head") + " " + c.s.get("un_" + u, u))

    items: list[dict] = []

    def say(metric, text):
        items.append({"metric": metric, "text": text})
    cl = a["by_class"]
    if cl:
        say("fleet", c.t("x_fleet", n=tot["machines"], k=len(cl), c=c.cls(cl[0]["key"]), cn=cl[0]["machines"]))
    say("consumption", c.t("x_use", cons=money(tot["consumption"]), allow=money(tot["allowance"]), util=pct(tot["utilization"]),
                           unused=money(tot["unused"]), upct=pct(_ratio(tot["unused"], tot["allowance"]))))
    if tot["in_excess"]:
        cost = c.t("x_exc_cost", cost=money(tot["excess_cost"])) if a["has_invoice"] and tot["cost_complete"] else ""
        say("excess", c.t("x_exc", n=tot["in_excess"], np=pct(_ratio(tot["in_excess"], tot["machines"]) if tot["machines"] else None),
                          exc=money(tot["excess_pages"]), cost=cost))
    if a["has_invoice"] and tot["cost_complete"]:
        say("cost", c.t("x_cost", cost=money(tot["cost"]), rent=money(tot["rent"]), exc=money(tot["excess_cost"]), cpp=money2(tot["cost_per_page"] or 0)))
    if a["by_location"]:
        top = a["by_location"][0]
        say("location", c.t("x_loc", n=top["name"], cons=money(top["consumption"]), share=pct(_ratio(top["consumption"], tot["consumption"]))))
    if a["by_branch"]:
        eb = max(a["by_branch"], key=lambda b: b["excess_pages"])
        say("branch", c.t("x_branch", n=a["by_branch"][0]["name"], cons=money(a["by_branch"][0]["consumption"]), e=eb["name"], exc=money(eb["excess_pages"])))
    if a["bands"]["under_utilised"]:
        say("under", c.t("x_under", n=a["bands"]["under_utilised"], t=th["low_utilization_pct"], v=a["bands"]["almost_unused"], vt=th["very_low_utilization_pct"]))
    if rec:
        s = rec["summary"]
        n = s["ok"] + s["diff"] + s["na"]
        say("recon", c.t("x_recon_ok", n=n, sales=money(invoice["totals"].get("sales_total", 0))) if not s["diff"] and not rec["unmapped_classes"]
            else c.t("x_recon_diff", d=s["diff"] + len(rec["unmapped_classes"]), n=n))
    elif not a["has_invoice"]:
        say("recon", c.t("x_recon_none"))
    for cv in caveats:
        items.append({"metric": "caveat", "text": cv})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items

    # ---------------------------------------------------------------- summary
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = _kpis(c, a, rec, invoice)
    sec.insights = [{"severity": "info" if i["metric"] != "caveat" else "warning", "text": i["text"], "metric": i["metric"]} for i in items]
    rm.sections.append(sec)

    # ---------------------------------------------------------------- fleet
    sec = ReportSection(c.t("s_fleet"), "fleet")
    sec.charts.append({"type": "bar", "title": c.t("ch_class"), "x": [c.cls(r["key"]) for r in cl], "series": [
        {"name": c.t("c_cons"), "values": [float(r["consumption"]) for r in cl]}, {"name": c.t("c_allow"), "values": [float(r["allowance"]) for r in cl]}]})
    sec.tables.append({"key": "classes", "title": c.t("t_class"), "columns": [
        col("name", c.t("c_class")), col("machines", c.t("c_machines"), "int"), col("allow", c.t("c_allow"), "int"), col("cons", c.t("c_cons"), "int"),
        col("util", c.t("c_util"), "pct"), col("exc", c.t("c_exc"), "int"), col("inexc", c.t("c_inexc"), "int"),
        col("rent", c.t("c_rent"), "money"), col("exccost", c.t("c_exccost"), "money"), col("cost", c.t("c_cost"), "money"),
        col("cpp", c.t("c_cpp"), "money3"), col("rentu", c.t("c_rentu"), "money"), col("rate", c.t("c_excr"), "money3")], "pdf_skip": ["rentu", "rate"],
        "rows": [{"name": c.cls(r["key"]), "machines": r["machines"], "allow": r["allowance"], "cons": r["consumption"], "util": r["utilization"],
                  "exc": r["excess_pages"], "inexc": r["in_excess"], "rentu": r["rent_unit"], "rent": r["rent"] if a["has_invoice"] else None,
                  "rate": r["excess_rate"], "exccost": r["excess_cost"] if a["has_invoice"] else None,
                  "cost": r["cost"] if r["cost_complete"] and a["has_invoice"] else None, "cpp": r["cost_per_page"]} for r in cl]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- usage
    sec = ReportSection(c.t("s_usage"), "usage")
    b = a["bands"]
    sec.charts.append({"type": "bar", "title": c.t("ch_bands"), "x": [c.t("b_almost"), c.t("b_low"), c.t("b_mid"), c.t("b_high"), c.t("b_over")],
                       "series": [{"name": c.t("c_machines"), "values": [b["almost_unused"], b["under_utilised"] - b["almost_unused"], b["low_to_50"], b["50_to_100"], b["over_100"]]}]})
    sec.charts.append({"type": "bar", "title": c.t("ch_exc"), "x": [c.cls(r["key"]) for r in cl], "series": [
        {"name": c.t("c_exc"), "values": [float(r["excess_pages"]) for r in cl]}]})
    sec.tables.append({"key": "bands", "title": c.t("t_bands"), "columns": [col("band", c.t("c_key")), col("n", c.t("c_machines"), "int")],
                       "rows": [{"band": c.t("b_almost"), "n": b["almost_unused"]}, {"band": c.t("b_low"), "n": b["under_utilised"] - b["almost_unused"]},
                                {"band": c.t("b_mid"), "n": b["low_to_50"]}, {"band": c.t("b_high"), "n": b["50_to_100"]},
                                {"band": c.t("b_over"), "n": b["over_100"]}]})
    mcols = [col("branch", c.t("c_branch")), col("cls", c.t("c_class")), col("loc", c.t("c_loc")), col("cons", c.t("c_cons"), "int"),
             col("allow", c.t("c_allow"), "int"), col("util", c.t("c_util"), "pct")]
    sec.tables.append({"key": "under", "title": c.t("t_under"), "columns": mcols + [col("unused", c.t("c_unused"), "int")],
                       "rows": [{"branch": r["branch_display"], "cls": c.cls(r["class_key"]), "loc": r.get("location_group") or "—", "cons": r["cons"],
                                 "allow": r["package"], "util": r["util"], "unused": r["unused"]} for r in a["under_utilised"]], "pdf_rows": 20})
    sec.tables.append({"key": "exceeding", "title": c.t("t_exceed"), "columns": mcols[:3] + [
        col("cons", c.t("c_cons"), "int"), col("allow", c.t("c_allow"), "int"), col("exc", c.t("c_exc"), "int"), col("excpct", c.t("c_excpct"), "pct"),
        col("exccost", c.t("c_exccost"), "money")],
        "rows": [{"branch": r["branch_display"], "cls": c.cls(r["class_key"]), "loc": r.get("location_group") or "—", "cons": r["cons"], "allow": r["package"],
                  "exc": r["exc"], "excpct": _ratio(r["exc"], r["package"]), "exccost": r["excess_cost"]} for r in a["exceeding"]], "pdf_rows": 20})
    sec.tables.append({"key": "top", "title": c.t("t_top"), "columns": mcols, "rows": [
        {"branch": r["branch_display"], "cls": c.cls(r["class_key"]), "loc": r.get("location_group") or "—", "cons": r["cons"], "allow": r["package"],
         "util": r["util"]} for r in a["top_consumers"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- cost
    sec = ReportSection(c.t("s_cost"), "cost")
    if a["has_invoice"]:
        rows = [r for r in cl if r["rent"] is not None]
        sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_cost"), "x": [c.cls(r["key"]) for r in rows], "series": [
            {"name": c.t("c_rent"), "values": [float(r["rent"]) for r in rows]}, {"name": c.t("c_exccost"), "values": [float(r["excess_cost"]) for r in rows]}]})
        sec.tables.append({"key": "cost_class", "title": c.t("s_cost"), "columns": [
            col("name", c.t("c_class")), col("rent", c.t("c_rent"), "money"), col("exccost", c.t("c_exccost"), "money"), col("cost", c.t("c_cost"), "money"),
            col("cpp", c.t("c_cpp"), "money3")], "rows": [{"name": c.cls(r["key"]), "rent": r["rent"], "exccost": r["excess_cost"],
                                                          "cost": r["cost"] if r["cost_complete"] else None, "cpp": r["cost_per_page"]} for r in cl]})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_cost")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- locations
    sec = ReportSection(c.t("s_loc"), "locations")
    if a["by_location"]:
        loc = a["by_location"]
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_loc"), "x": [r["name"] for r in loc[:12]],
                           "series": [{"name": c.t("c_cons"), "values": [float(r["consumption"]) for r in loc[:12]]}]})
        sec.tables.append({"key": "locations", "title": c.t("t_loc"), "columns": [
            col("name", c.t("c_loc")), col("machines", c.t("c_machines"), "int"), col("cons", c.t("c_cons"), "int"), col("share", c.t("c_share"), "pct"),
            col("util", c.t("c_util"), "pct"), col("exc", c.t("c_exc"), "int"), col("cost", c.t("c_cost"), "money")],
            "rows": [{"name": r["name"], "machines": r["machines"], "cons": r["consumption"], "share": _ratio(r["consumption"], tot["consumption"]),
                      "util": r["utilization"], "exc": r["excess_pages"], "cost": r["cost"] if r["cost_complete"] and a["has_invoice"] else None} for r in loc]})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_location")})
    br = a["by_branch"]
    n = int(th["top_n"])
    sec.charts.append({"type": "bar", "horizontal": True, "drill": "branch", "title": c.t("ch_top"), "x": [r["name"] for r in br[:n]],
                       "series": [{"name": c.t("c_cons"), "values": [float(r["consumption"]) for r in br[:n]]}]})
    sec.tables.append({"key": "branches", "title": c.t("t_branch"), "columns": [
        col("rank", c.t("c_rank"), "int"), col("name", c.t("c_branch")), col("loc", c.t("c_loc")), col("machines", c.t("c_machines"), "int"),
        col("cons", c.t("c_cons"), "int"), col("util", c.t("c_util"), "pct"), col("exc", c.t("c_exc"), "int"), col("cost", c.t("c_cost"), "money")],
        "rows": [{"rank": i, "name": r["name"], "loc": r.get("location") or "—", "machines": r["machines"], "cons": r["consumption"], "util": r["utilization"],
                  "exc": r["excess_pages"], "cost": r["cost"] if r["cost_complete"] and a["has_invoice"] else None} for i, r in enumerate(br, 1)], "pdf_rows": 20})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- reconciliation
    sec = ReportSection(c.t("s_recon"), "reconciliation")
    if rec and invoice:
        sec.tables.append({"key": "invoice", "title": c.t("t_inv"), "columns": [col("k", c.t("c_key")), col("v", c.t("c_val"))], "rows": [
            {"k": c.t("iv_internal"), "v": invoice["internal_no"]}, {"k": c.t("iv_electronic"), "v": invoice["electronic_id"]},
            {"k": c.t("iv_issued"), "v": str(invoice["issued_on"] or "")}, {"k": c.t("iv_status"), "v": invoice["status"]},
            {"k": c.t("iv_seller"), "v": invoice["seller_name"]}, {"k": c.t("iv_buyer"), "v": invoice["buyer_name"]},
            {"k": c.t("iv_lines"), "v": str(len(invoice["lines"]))},
            {"k": c.t("iv_sales"), "v": money2(invoice["totals"].get("sales_total", 0))}, {"k": c.t("iv_vat"), "v": money2(invoice["totals"].get("vat", 0))},
            {"k": c.t("iv_wht"), "v": money2(invoice["totals"].get("withholding", 0))}, {"k": c.t("iv_grand"), "v": money2(invoice["totals"].get("grand_total", 0))}]})
        cc = [col("subject", c.t("c_subject")), col("check", c.t("c_check")), col("expected", c.t("c_expected"), "num"), col("invoiced", c.t("c_invoiced"), "num"),
              col("diff", c.t("c_diff"), "snum"), col("status", c.t("c_status")), col("ref", c.t("c_ref"))]
        for key, title, grp in (("recon", "t_recon", "primary"), ("recon_support", "t_support", "supporting"), ("recon_internal", "t_internal", "invoice_internal")):
            rows = [{"subject": ck["subject"], "check": c.s["rk_" + ck["id"].rsplit("_", 1)[0]] if "rk_" + ck["id"].rsplit("_", 1)[0] in c.s
                     else c.s.get("rk_" + ck["id"], ck["id"]), "expected": ck["expected"], "invoiced": ck["invoiced"], "diff": ck["diff"],
                     "status": c.t("st_" + ck["status"]), "ref": "; ".join(ck["refs"])} for ck in rec["checks"] if ck["group"] == grp]
            if rows:
                sec.tables.append({"key": key, "title": c.t(title), "columns": cc, "rows": rows, "pdf_rows": 40})
        if rec["unmapped_classes"]:
            sec.insights.append({"severity": "warning", "text": ", ".join(c.cls(k) for k in rec["unmapped_classes"]) + " — no invoice line covers this class"})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_invoice_reconciliation")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- evidence
    sec = ReportSection(c.t("s_evidence"), "evidence")
    sec.insights.append({"severity": "warning", "text": c.t("e_note")})
    if evidence:
        if evidence["status"] == "processing":
            sec.insights.append({"severity": "info", "text": c.t("ev_processing")})
        elif evidence["status"] == "failed":
            sec.insights.append({"severity": "warning", "text": c.t("ev_failed") + (f": {evidence['error']}" if evidence.get("error") else "")})
        else:
            sec.tables.append({"key": "evidence", "title": c.t("t_evid"), "columns": [
                col("page", c.t("c_page"), "int"), col("counter", c.t("c_counter"), "int"), col("printed", c.t("c_printed")),
                col("status", c.t("c_status")), col("machine", c.t("c_machine")), col("note", c.t("c_note"))],
                "rows": [{"page": p["page_no"], "counter": p["counter"], "printed": p["printed_at"] or "", "status": c.t("ev_" + p["status"]),
                          "machine": p["machine"] or "", "note": c.s.get("evn_" + p["status"], "")} for p in evidence["pages"]], "pdf_rows": 60})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- quality
    sec = ReportSection(c.t("s_quality"), "quality")
    sec.insights += [{"severity": "info", "text": x} for x in caveats]
    sec.tables.append({"key": "sources", "title": c.t("t_sources"), "columns": [col("role", c.t("c_src")), col("file", c.t("c_key")), col("rows", c.t("c_count"), "int"),
                                                                                   col("status", c.t("c_status"))],
                       "rows": [{"role": s["role"], "file": s["file_name"], "rows": s["rows"], "status": s["status"]} for s in cycle["sources"]]})
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [
        col("message", c.t("c_issue")), col("severity", c.t("c_sev")), col("count", c.t("c_count"), "int"), col("examples", c.t("c_examples"))],
        "rows": [{"message": i["message"], "severity": c.t("sev_" + i["severity"]), "count": i["count"], "examples": " | ".join(i["examples"][:4])}
                 for i in issues], "pdf_rows": 25})
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("name", c.t("c_name")), col("value", c.t("c_val")), col("source", c.t("c_source"))],
                       "rows": [{"name": k, "value": th[k], "source": th_origin[k]} for k in th]})
    rm.sections.append(sec)
    return rm


def _ratio(a, b):
    return float(Decimal(str(a)) / Decimal(str(b)) * 100) if b else None


def _kpis(c: C, a: dict, rec, invoice) -> list[dict]:
    t = a["totals"]
    k = [{"label": c.t("k_machines"), "value": money(t["machines"]), "sub": f"{len(a['by_class'])} {c.t('c_class')}"},
         {"label": c.t("k_cons"), "value": money(t["consumption"]), "sub": c.t("pages")},
         {"label": c.t("k_allow"), "value": money(t["allowance"]), "sub": c.t("pages")},
         {"label": c.t("k_util"), "value": pct(t["utilization"]), "sub": f"{money(t['unused'])} {c.t('k_unused')}"},
         {"label": c.t("k_exc"), "value": money(t["excess_pages"]), "sub": c.t("pages")},
         {"label": c.t("k_inexc"), "value": str(t["in_excess"]), "sub": pct(_ratio(t["in_excess"], t["machines"]))},
         {"label": c.t("k_under"), "value": str(a["bands"]["under_utilised"]), "sub": f"{a['bands']['almost_unused']} ≈ 0"}]
    if a["has_invoice"] and t["cost_complete"]:
        k += [{"label": c.t("k_rent"), "value": money(t["rent"]), "sub": c.t("egp")}, {"label": c.t("k_exccost"), "value": money(t["excess_cost"]), "sub": c.t("egp")},
              {"label": c.t("k_cost"), "value": money(t["cost"]), "sub": c.t("egp")}, {"label": c.t("k_cpp"), "value": money2(t["cost_per_page"] or 0), "sub": c.t("egp")}]
    if invoice:
        k.append({"label": c.t("k_inv"), "value": money(invoice["totals"].get("grand_total", 0)), "sub": c.t("egp")})
    if rec:
        s = rec["summary"]
        bad = s["diff"] + len(rec["unmapped_classes"])
        k.append({"label": c.t("k_recon"), "value": c.t("recon_ok") if not bad else c.t("recon_diff", n=bad), "sub": f"{s['ok']}/{s['ok'] + s['diff'] + s['na']}",
                  "tone": "" if not bad else "up"})
    return k


# ------------------------------------------------------------------------------------------------ trend report
def build_trend_report(cycles_meta: list[dict], trend: dict, lang: str = "ar") -> ReportModel:
    c = C(lang)
    rows = trend["rows"]
    first, last = rows[0]["period"], rows[-1]["period"]
    rm = ReportModel(title=c.t("title_trend"), period_label=f"{period_label(lang, first)} – {period_label(lang, last)}", sections=[], lang=lang)
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": "", "file_hash": "",
               "filters": {"active": {}, "options": {}, "dimensions": []}}
    items = []
    if len(rows) >= 2:
        a, b = rows[-2], rows[-1]
        d = b["consumption"] - a["consumption"]
        items.append({"metric": "trend", "text": c.t("x_trend", a=period_label(lang, a["period"]), b=period_label(lang, b["period"]), d=smoney(d),
                                                     p=spct(b.get("consumption_mom_pct")))})
    if trend["indicative"]:
        items.append({"metric": "caveat", "text": c.s["i_single"] if lang else ""})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    rm.sections.append(sec)
    sec = ReportSection(c.t("s_trend"), "trend")
    x = [period_label(lang, r["period"], True) for r in rows]
    sec.charts.append({"type": "bar", "title": c.t("ch_tcons"), "x": x, "series": [
        {"name": c.t("tr_cons"), "values": [float(r["consumption"]) for r in rows]}, {"name": c.t("tr_allow"), "values": [float(r["allowance"]) for r in rows]}]})
    if any(r["cost"] is not None for r in rows):
        sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_tcost"), "x": x, "series": [
            {"name": c.t("tr_rent"), "values": [float(r["rent"]) for r in rows]}, {"name": c.t("tr_exccost"), "values": [float(r["excess_cost"]) for r in rows]}]})
    sec.tables.append({"key": "trend", "title": c.t("t_trend"), "columns": [
        col("period", c.t("c_period")), col("machines", c.t("tr_machines"), "int"), col("cons", c.t("tr_cons"), "int"), col("allow", c.t("tr_allow"), "int"),
        col("util", c.t("tr_util"), "pct"), col("exc", c.t("tr_exc"), "int"), col("rent", c.t("tr_rent"), "money"), col("exccost", c.t("tr_exccost"), "money"),
        col("cost", c.t("tr_cost"), "money"), col("inv", c.t("tr_inv"), "money"), col("mom", c.t("c_mom"), "smoney"), col("mompct", c.t("c_mompct"), "spct"),
        col("recon", c.t("c_recon"))],
        "rows": [{"period": period_label(lang, r["period"]), "machines": r["machines"], "cons": r["consumption"], "allow": r["allowance"], "util": r["utilization"],
                  "exc": r["excess_pages"], "rent": r["rent"], "exccost": r["excess_cost"], "cost": r["cost"], "inv": r["invoice_total"],
                  "mom": r.get("consumption_mom"), "mompct": r.get("consumption_mom_pct"),
                  "recon": ("" if not r["recon"] else (c.t("recon_ok") if not r["recon"]["diff"] else c.t("recon_diff", n=r["recon"]["diff"])))} for r in rows]})
    if trend["continuity"]:
        sec.insights.append({"severity": "info", "text": c.t("cont_note")})
        sec.tables.append({"key": "continuity", "title": c.t("t_cont"), "columns": [col("a", c.t("c_period")), col("n", c.t("c_machines"), "int"),
                                                                                       col("ok", c.t("st_ok"), "int"), col("bad", c.t("st_diff"), "int")],
                           "rows": [{"a": f"{period_label(lang, x['from'])} → {period_label(lang, x['to'])}", "n": x["machines"], "ok": x["continuous"], "bad": x["broken"]}
                                    for x in trend["continuity"]]})
    rm.sections.append(sec)
    return rm
