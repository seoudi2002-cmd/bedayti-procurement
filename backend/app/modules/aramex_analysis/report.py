"""ReportModel for the Aramex module. Primary goal: per branch, shipments sent / received and their cost, every month, with the
change against the previous month. Everything else (cities, weights, services, charges, exceptions) is supporting.
Every sentence of the summary is generated from computed numbers; what the files do not support is stated as «not available»."""
from datetime import datetime, timezone
from decimal import Decimal

from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "تحليل مصروفات Aramex", "s_summary": "الملخص التنفيذي", "s_branches": "أداء الفروع: الصادر والوارد", "s_monthly": "الاتجاه الشهري والمقارنة",
        "s_alloc": "جودة ربط الشحنات بالفروع", "s_recon": "مطابقة الفاتورة مع الكشف", "s_support": "تحليلات مساندة", "s_exc": "الاستثناءات", "s_quality": "جودة البيانات والإعدادات",
        "scope_all": "كل الفواتير المرفوعة", "scope_month": "شهر {m}", "scope_inv": "فاتورة {i}", "source": "المصادر", "filtered": "عرض مفلتر",
        "k_n": "الشحنات", "k_net": "التكلفة قبل الضريبة", "k_gross": "الإجمالي شامل الضريبة", "k_avg": "متوسط تكلفة الشحنة", "k_branches": "فروع لها حركة",
        "k_conf": "شحنات مربوطة بيقين (الطرفان)", "k_unalloc": "Unallocated / يحتاج مراجعة", "k_kg": "الوزن المحاسبي", "egp": "ج.م", "kg": "كجم", "ship": "شحنة",
        "hq": "المركز الرئيسي (Head Office)", "unalloc": "Unallocated / يحتاج مراجعة", "total": "الإجمالي",
        "c_branch": "الفرع", "c_sent_n": "شحنات صادرة", "c_sent_c": "تكلفة الصادر", "c_recv_n": "شحنات واردة", "c_recv_c": "تكلفة الوارد", "c_tot_n": "إجمالي الشحنات",
        "c_tot_c": "إجمالي التكلفة", "c_avg": "متوسط تكلفة الشحنة", "c_month": "الشهر", "c_n": "الشحنات", "c_net": "قبل الضريبة", "c_gross": "شامل الضريبة", "c_d": "التغير",
        "c_dpct": "التغير %", "c_cur_n": "شحنات الشهر", "c_prev_n": "الشهر السابق", "c_cur_c": "تكلفة الشهر", "c_prev_c": "تكلفة السابق", "c_dn": "تغير العدد",
        "c_dnp": "تغير العدد %", "c_dc": "تغير التكلفة", "c_dcp": "تغير التكلفة %", "c_partial": "ملاحظة", "c_side": "الطرف", "c_kind": "التصنيف", "c_cost": "التكلفة",
        "c_share": "النسبة %", "c_reason": "السبب", "c_name": "الاسم", "c_key": "البيان", "c_val": "القيمة", "c_source": "المصدر", "c_issue": "الملاحظة", "c_sev": "الأهمية",
        "c_count": "العدد", "c_examples": "أمثلة", "c_inv": "الفاتورة", "c_pdf": "بنود PDF", "c_xlsx": "صفوف Excel", "c_stated": "المعلن في الفاتورة", "c_rows": "مجموع الشحنات",
        "c_diff": "الفرق", "c_status": "الحالة", "c_check": "الاختبار", "c_exp": "حسب الكشف", "c_inv_v": "حسب الفاتورة", "c_ref": "المرجع", "c_city": "المدينة / المسار",
        "c_kg": "كجم", "c_band": "الشريحة", "c_flag": "الاستثناء", "c_awb": "AWB", "c_date": "التاريخ", "c_orig": "المنشأ", "c_dest": "الوجهة", "c_flags": "الاستثناءات",
        "c_wt": "الوزن", "c_item": "البند", "c_pct": "نسبة %", "c_setting": "الإعداد", "c_origin": "المصدر",
        "t_branch": "الفروع: الصادر والوارد", "t_hq_note": "الجدول", "t_mom": "المقارنة مع الشهر السابق لكل جهة", "t_months": "المؤشرات حسب الشهر", "t_pm_n": "الشحنات (صادر + وارد) حسب الجهة والشهر",
        "t_pm_c": "التكلفة قبل الضريبة (صادر + وارد) حسب الجهة والشهر", "t_quality": "نسب الربط حسب الطرف", "t_reasons": "أسباب Unallocated", "t_unreg": "فروع مكتوبة في الملف وغير مسجلة في سجل الفروع",
        "t_invctl": "ضبط الفواتير: المعلن مقابل مجموع الشحنات", "t_checks": "اختبارات المطابقة", "t_recon_sum": "ملخص المطابقة لكل فاتورة", "t_ctl": "ضبط التجميع",
        "t_orig": "أعلى مدن المنشأ", "t_dest": "أعلى مدن الوجهة", "t_routes": "أعلى المسارات", "t_serv": "الخدمات (كود المنتج كما في الفاتورة)", "t_weight": "شرائح الوزن المحاسبي",
        "t_charges": "تركيب التكلفة", "t_excsum": "ملخص الاستثناءات", "t_excrows": "شحنات مستثناة (أمثلة)", "t_sources": "الملفات المرفوعة", "t_issues": "ملاحظات جودة البيانات",
        "t_settings": "الإعدادات المستخدمة", "t_na": "غير متاح (لا تدعمه الملفات)", "t_merge": "شحنات في مصدر واحد فقط",
        "ch_top": "أعلى الفروع تكلفة (صادر + وارد)", "ch_month": "التكلفة قبل الضريبة شهريًا",
        "sender": "المرسل", "receiver": "المستلم", "k_branch": "فرع", "k_head_office": "مركز رئيسي", "k_unallocated": "Unallocated",
        "r_no_branch_evidence": "لا دليل صريح على الفرع (اسم عام أو شخص أو مدينة فقط)", "r_conflicting_evidence": "أدلة متعارضة (اسم فرع مع مؤشر مركز رئيسي)",
        "r_conflicting_branches": "أكثر من فرع في الطرف نفسه", "r_register_unallocated": "الاسم مسجل في السجل كغير موزع",
        "partial": "شهر جزئي: الفواتير المرفوعة لا تغطي كل أيامه", "prev_missing": "لا يوجد شهر سابق مرفوع للمقارنة", "n_a": "غير متاح",
        "f_branches": "الجهة (فرع/مقر)", "f_services": "الخدمة", "f_cities": "المدينة",
        "x_total": "{n} شحنة بتكلفة {net} ج.م قبل الضريبة ({gross} ج.م شامل الضريبة) بمتوسط {avg} ج.م للشحنة، وأعلى فرع تكلفة «{top}» ({topc} ج.م صادر + وارد).",
        "x_alloc": "ربط الشحنات: {both} من الشحنات الطرفان فيها مؤكدان؛ المرسل مؤكد في {s} والمستلم في {r}؛ والباقي Unallocated ({u} ج.م).",
        "x_alloc_low": "نسبة الربط المؤكد أقل من {t}%: أرقام الفروع الفردية تغطي جزءًا فقط من الشحنات، ويظهر الباقي في Unallocated دون توزيع تقديري.",
        "x_mom": "{m} مقابل {p}: عدد الشحنات {d} ({dp})، والتكلفة {dc} ج.م ({dcp}).",
        "x_mom_big": "تغيرات تتجاوز {t}%: {names}.", "x_prev_missing": "لا يوجد شهر سابق مرفوع، فمقارنة الشهر غير متاحة.",
        "x_recon_ok": "مطابقة الفاتورة {i} مع الكشف: كل الاختبارات ({n}) متطابقة.", "x_recon_diff": "مطابقة الفاتورة {i} مع الكشف: {d} اختبار فيه فرق (انظر المطابقة).",
        "x_hq": "المركز الرئيسي: {sn} شحنة صادرة ({sc} ج.م) و{rn} واردة ({rc} ج.م).",
        "i_cost": "التكلفة الرئيسية قبل الضريبة (ما تذكره الفاتورة كـ «Net Amount»)؛ الإجمالي شامل الضريبة مؤشر إضافي. تكلفة الشحنة تنسب كاملة لمرسلها ولمستلمها كلٌّ في عموده دون تقسيم، فمجموع «إجمالي التكلفة» للفروع يعد الشحنة بين طرفين مرتين؛ ويطابق مجموع الصادر ومجموع الوارد إجمالي النطاق.",
        "i_month": "الشهر يحدد بتاريخ الاستلام الفعلي في الفاتورة PDF وليس بتاريخ الاستحقاق في Excel.",
        "i_alloc": "لا تُحدَّد الجهة بالمدينة وحدها: الفرع يُحدد باسم صريح في الملف («شركة بدايتي فرع …»)، والمقر بقاعدة المقر المعتمدة، وغير ذلك Unallocated.",
        "i_filtered": "العرض مفلتر؛ ضبط الفواتير لا يظهر مع الفلاتر.", "i_partial_all": "الأشهر الأولى والأخيرة قد تكون جزئية حسب نطاق تواريخ الفواتير المرفوعة.",
        "i_rate_unset": "لم تُدخل بطاقة الأسعار في الإعدادات؛ فحص الأسعار غير متاح.", "i_rate_ok": "فحص بطاقة الأسعار: {off} شحنة من {n} لا يتبع البطاقة.",
        "i_ratio": "الرسوم الأخرى تساوي {lo}–{hi} من الأساسي ({k} قيمة مختلفة)؛ تركيبها غير مفصل في الفاتورة ولم يُفكَّك.",
        "i_volu": "في {n} شحنة الوزن المحاسبي أكبر من الفعلي ({kg} كجم زيادة)؛ الأثر المالي غير متاح لأن سعر الكيلو حسب المنطقة غير معروف.",
        "na_governorate": "التكلفة حسب المحافظة: الملفات تذكر مدنًا فقط ولا تذكر المحافظة", "na_zone": "التكلفة حسب منطقة Aramex (1–6): لا يوجد جدول معتمد يربط المدن بالمناطق",
        "na_rates": "فحص الأسعار مقابل بطاقة العقد: بطاقة الأسعار غير مدخلة", "na_budget": "المقارنة بميزانية أو بالعام السابق: غير موجودة", "na_prev": "مقارنة الشهر السابق: لا يوجد شهر سابق مرفوع",
        "ex_heavy": "شحنة ثقيلة", "ex_volumetric": "وزن محاسبي أكبر من الفعلي", "ex_same_city": "منشأ = وجهة", "ex_weekend": "استلام في عطلة الأسبوع", "ex_multi_piece": "أكثر من قطعة",
        "ex_cost_outlier": "تكلفة أعلى من المعتاد", "ex_rate_off_card": "السعر خارج بطاقة العقد", "ex_allocation_conflict": "أدلة ربط متعارضة",
        "ck_lines": "عدد الشحنات", "ck_awb_missing_in_sheet": "بنود فاتورة غير موجودة في الكشف", "ck_awb_missing_in_invoice": "صفوف كشف غير موجودة في الفاتورة", "ck_base_per_awb": "الرسم الأساسي لكل AWB",
        "ck_other_per_awb": "الرسوم الأخرى لكل AWB", "ck_net_per_awb": "صافي بند الفاتورة = أساسي + أخرى", "ck_weight_per_awb": "الوزن المحاسبي لكل AWB", "ck_route_per_awb": "نص المنشأ والوجهة",
        "ck_sum_base": "Σ الرسم الأساسي", "ck_sum_other": "Σ الرسوم الأخرى", "ck_net_total": "صافي الفاتورة مقابل الكشف", "ck_vat_total": "ضريبة القيمة المضافة (مع التسوية)",
        "ck_grand_total": "إجمالي الفاتورة (مع التسوية)", "ck_sheet_total_row": "صف الإجمالي في الكشف", "st_ok": "مطابق", "st_diff": "فرق",
        "sev_critical": "حرج", "sev_warning": "تنبيه", "sev_info": "للعلم", "mc": "ضبط: الصادر = الوارد = إجمالي النطاق", "mc_ok": "سليم", "mc_bad": "غير سليم", "dup": "AWB مكرر",
        "sets_hq": "قاعدة المقر (مواقع / أسماء)", "ref_docs": "ملحق العقد الممسوح (مرجع فقط، لا تُقرأ منه أرقام)", "no_rows": "لا شحنات",
        "i_adj": "الإجمالي شامل الضريبة محسوب من بنود الشحنات ({lines} ج.م)، وإجمالي الفاتورة {inv} ج.م؛ الفرق {adj} ج.م هو تسوية تقريب الضريبة المسجلة في الكشف خارج الشحنات.",
        "i_mom_partial": "أحد الشهرين أو كلاهما جزئي (الفواتير المرفوعة لا تغطي كل أيامه)؛ فالتغير يعكس اختلاف عدد الأيام أيضًا، ويُقرأ بحذر.",
        "x_support_diff": "{n} اختبار مساند فيه فرق (نصوص المنشأ والوجهة المقتطعة في PDF)؛ لا يغيّر أي رقم.", "mc_note": "ضبط التجميع", "reason_none": "—", "band": "حتى {hi} كجم", "band_mid": "{lo}–{hi} كجم", "band_top": "أكثر من {lo} كجم",
    },
    "en": {
        "title": "Aramex spend analysis", "s_summary": "Executive summary", "s_branches": "Branch performance: sent and received", "s_monthly": "Monthly trend and comparison",
        "s_alloc": "Branch-allocation quality", "s_recon": "Invoice vs sheet reconciliation", "s_support": "Supporting analyses", "s_exc": "Exceptions", "s_quality": "Data quality and settings",
        "scope_all": "All uploaded invoices", "scope_month": "Month {m}", "scope_inv": "Invoice {i}", "source": "Sources", "filtered": "Filtered view",
        "k_n": "Shipments", "k_net": "Cost before tax", "k_gross": "Total incl. tax", "k_avg": "Average cost per shipment", "k_branches": "Branches with activity",
        "k_conf": "Confirmed on both sides", "k_unalloc": "Unallocated / needs review", "k_kg": "Billed weight", "egp": "EGP", "kg": "kg", "ship": "shipments",
        "hq": "Head Office", "unalloc": "Unallocated / needs review", "total": "Total",
        "c_branch": "Branch", "c_sent_n": "Shipments sent", "c_sent_c": "Cost sent", "c_recv_n": "Shipments received", "c_recv_c": "Cost received", "c_tot_n": "Total shipments",
        "c_tot_c": "Total cost", "c_avg": "Avg cost per shipment", "c_month": "Month", "c_n": "Shipments", "c_net": "Before tax", "c_gross": "Incl. tax", "c_d": "Change",
        "c_dpct": "Change %", "c_cur_n": "Shipments this month", "c_prev_n": "Previous month", "c_cur_c": "Cost this month", "c_prev_c": "Previous cost", "c_dn": "Change in count",
        "c_dnp": "Count change %", "c_dc": "Cost change", "c_dcp": "Cost change %", "c_partial": "Note", "c_side": "Side", "c_kind": "Class", "c_cost": "Cost",
        "c_share": "Share %", "c_reason": "Reason", "c_name": "Name", "c_key": "Item", "c_val": "Value", "c_source": "Source", "c_issue": "Issue", "c_sev": "Severity",
        "c_count": "Count", "c_examples": "Examples", "c_inv": "Invoice", "c_pdf": "PDF lines", "c_xlsx": "Excel rows", "c_stated": "Stated on invoice", "c_rows": "Σ shipments",
        "c_diff": "Difference", "c_status": "Status", "c_check": "Check", "c_exp": "Per sheet", "c_inv_v": "Per invoice", "c_ref": "Reference", "c_city": "City / route",
        "c_kg": "kg", "c_band": "Band", "c_flag": "Exception", "c_awb": "AWB", "c_date": "Date", "c_orig": "Origin", "c_dest": "Destination", "c_flags": "Exceptions",
        "c_wt": "Weight", "c_item": "Item", "c_pct": "%", "c_setting": "Setting", "c_origin": "Origin",
        "t_branch": "Branches: sent and received", "t_hq_note": "Table", "t_mom": "Comparison with the previous month, per party", "t_months": "Indicators by month", "t_pm_n": "Shipments (sent + received) by party and month",
        "t_pm_c": "Cost before tax (sent + received) by party and month", "t_quality": "Allocation rates by side", "t_reasons": "Why shipments are Unallocated", "t_unreg": "Branch names written in the file but not in the branch register",
        "t_invctl": "Invoice control: stated vs Σ shipments", "t_checks": "Reconciliation checks", "t_recon_sum": "Reconciliation summary per invoice", "t_ctl": "Aggregation control",
        "t_orig": "Top origin cities", "t_dest": "Top destination cities", "t_routes": "Top routes", "t_serv": "Services (product code as on the invoice)", "t_weight": "Billed-weight bands",
        "t_charges": "Cost composition", "t_excsum": "Exception summary", "t_excrows": "Exception shipments (examples)", "t_sources": "Uploaded files", "t_issues": "Data-quality notes",
        "t_settings": "Settings used", "t_na": "Not available (the files do not support it)", "t_merge": "Shipments in one source only",
        "ch_top": "Top branches by cost (sent + received)", "ch_month": "Cost before tax per month",
        "sender": "Sender", "receiver": "Receiver", "k_branch": "Branch", "k_head_office": "Head Office", "k_unallocated": "Unallocated",
        "r_no_branch_evidence": "No explicit branch evidence (generic name, a person, or a city only)", "r_conflicting_evidence": "Conflicting evidence (a branch name with a Head Office marker)",
        "r_conflicting_branches": "More than one branch on the same side", "r_register_unallocated": "The register lists the name as unallocated",
        "partial": "Partial month: the uploaded invoices do not cover all its days", "prev_missing": "No previous month uploaded to compare with", "n_a": "n/a",
        "f_branches": "Party (branch / Head Office)", "f_services": "Service", "f_cities": "City",
        "x_total": "{n} shipments costing {net} EGP before tax ({gross} EGP incl. tax), averaging {avg} EGP per shipment; the costliest branch is «{top}» ({topc} EGP sent + received).",
        "x_alloc": "Allocation: both sides are confirmed for {both} of shipments; the sender is confirmed for {s} and the receiver for {r}; the rest is Unallocated ({u} EGP).",
        "x_alloc_low": "The confirmed-allocation rate is below {t}%: individual branch figures cover only part of the shipments; the rest stays in Unallocated with no estimated split.",
        "x_mom": "{m} vs {p}: shipments {d} ({dp}), cost {dc} EGP ({dcp}).",
        "x_mom_big": "Changes above {t}%: {names}.", "x_prev_missing": "No previous month is uploaded, so the month comparison is not available.",
        "x_recon_ok": "Invoice {i} vs its sheet: all checks ({n}) agree.", "x_recon_diff": "Invoice {i} vs its sheet: {d} check(s) differ (see reconciliation).",
        "x_hq": "Head Office: {sn} shipments sent ({sc} EGP) and {rn} received ({rc} EGP).",
        "i_cost": "The main cost is before tax (the invoice's «Net Amount»); the total including tax is an additional indicator. A shipment's whole cost is attributed to its sender and to its receiver, each in its own column, never split: the branches' «total cost» counts a shipment between two parties twice; Σ sent and Σ received each equal the scope total.",
        "i_month": "The month is set by the actual pick-up date on the invoice PDF, not by the due date in the Excel.",
        "i_alloc": "A party is never decided from its city alone: a branch needs an explicit name in the file («<company> branch …»), Head Office follows the approved Head Office rule, everything else is Unallocated.",
        "i_filtered": "Filtered view; the invoice controls are not shown with filters.", "i_partial_all": "The first and last months can be partial, depending on the dates covered by the uploaded invoices.",
        "i_rate_unset": "The rate card is not entered in settings; the price check is not available.", "i_rate_ok": "Rate-card check: {off} of {n} shipments do not follow the card.",
        "i_ratio": "Other charges equal {lo}–{hi} of the base charge ({k} distinct values); their composition is not itemised on the invoice and was not decomposed.",
        "i_volu": "In {n} shipments the billed weight exceeds the actual weight ({kg} kg more); the cost impact is not available because the per-kg price by zone is unknown.",
        "na_governorate": "Cost by governorate: the files give cities only, no governorate", "na_zone": "Cost by Aramex zone (1–6): no approved table maps cities to zones",
        "na_rates": "Price check against the contract card: the rate card is not entered", "na_budget": "Comparison with a budget or last year: none provided", "na_prev": "Previous-month comparison: no previous month uploaded",
        "ex_heavy": "Heavy shipment", "ex_volumetric": "Billed weight above actual", "ex_same_city": "Origin = destination", "ex_weekend": "Pick-up on a weekend day", "ex_multi_piece": "More than one piece",
        "ex_cost_outlier": "Cost above the norm", "ex_rate_off_card": "Price off the contract card", "ex_allocation_conflict": "Conflicting allocation evidence",
        "ck_lines": "Number of shipments", "ck_awb_missing_in_sheet": "Invoice lines missing from the sheet", "ck_awb_missing_in_invoice": "Sheet rows missing from the invoice", "ck_base_per_awb": "Base charge per AWB",
        "ck_other_per_awb": "Other charges per AWB", "ck_net_per_awb": "Invoice line net = base + other", "ck_weight_per_awb": "Billed weight per AWB", "ck_route_per_awb": "Origin / destination text",
        "ck_sum_base": "Σ base charge", "ck_sum_other": "Σ other charges", "ck_net_total": "Invoice net vs the sheet", "ck_vat_total": "VAT (with the adjustment)",
        "ck_grand_total": "Invoice total (with the adjustment)", "ck_sheet_total_row": "The sheet's total row", "st_ok": "Match", "st_diff": "Differs",
        "sev_critical": "Critical", "sev_warning": "Warning", "sev_info": "Info", "mc": "Control: Σ sent = Σ received = scope total", "mc_ok": "OK", "mc_bad": "Not OK", "dup": "Duplicate AWB",
        "sets_hq": "Head Office rule (locations / names)", "ref_docs": "Scanned contract appendix (reference only; no figure is read from it)", "no_rows": "No shipments",
        "i_adj": "The total incl. tax is built from the shipment lines ({lines} EGP) while the invoice total is {inv} EGP; the {adj} EGP difference is the tax-rounding adjustment recorded in the sheet apart from the shipments.",
        "i_mom_partial": "One or both months are partial (the uploaded invoices do not cover all their days); the change also reflects the different number of days and should be read with care.",
        "x_support_diff": "{n} supporting check(s) differ (origin / destination text truncated in the PDF); no figure is affected.", "mc_note": "Aggregation control", "reason_none": "—", "band": "up to {hi} kg", "band_mid": "{lo}–{hi} kg", "band_top": "over {lo} kg",
    },
}


class C:
    def __init__(self, lang):
        self.lang, self.s = lang, T[lang]

    def t(self, key, **kw):
        return self.s[key].format(**kw) if kw else self.s[key]

    def party(self, p):
        return self.t("hq") if p["kind"] == "head_office" else self.t("unalloc") if p["kind"] == "unallocated" else p["name"]


def _fmt_month(lang, m, short=False):
    return period_label(lang, m, short)


def build_report(scope: dict, a: dict, invoices: list[dict], recons: dict, merge_exc: list[dict], issues: list[dict], sources: list[dict], th: dict, th_origin: dict,
                 settings_note: dict, unsupported: list[str], lang: str, filters: dict, dims: list[dict]) -> ReportModel:
    c = C(lang)
    tot, parties, ctrl, q = a["totals"], a["parties"], a["controls"], a["allocation"]
    label = c.t("scope_all") if scope["kind"] == "all" else c.t("scope_month", m=_fmt_month(lang, scope["month"])) if scope["kind"] == "month" else c.t("scope_inv", i=scope["label"])
    rm = ReportModel(title=c.t("title"), period_label=label, sections=[], lang=lang)
    rm.subtitle = f"{c.t('source')}: " + " · ".join(s["file_name"] for s in sources[:4]) + (" · " + c.t("filtered") if a["filtered"] else "")
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ", ".join(s["file_name"] for s in sources[:3]), "file_hash": "",
               "filters": {"active": filters, "options": {}, "dimensions": dims}}
    branches = [p for p in parties if p["kind"] == "branch"]
    hq = next((p for p in parties if p["kind"] == "head_office"), None)
    both_pct = q["both_confirmed_pct"]

    # ------------------------------------------------------------ executive summary
    items: list[dict] = []
    if tot["n"]:
        top = max(branches, key=lambda p: p["total_cost"], default=None)
        items.append({"metric": "total", "text": c.t("x_total", n=f"{tot['n']:,}", net=money2(tot["net"]), gross=money2(tot["gross"]), avg=money2(tot["avg_net"]),
                                                     top=top["name"] if top else "—", topc=money2(top["total_cost"]) if top else "—")})
        items.append({"metric": "alloc", "text": c.t("x_alloc", both=pct(both_pct), s=pct(q["sides"]["sender"]["confirmed_pct"]), r=pct(q["sides"]["receiver"]["confirmed_pct"]),
                                                      u=money2(sum((s["unallocated_cost"] for s in q["sides"].values()), Decimal(0))))})
        if both_pct is not None and both_pct < th["low_allocation_pct"]:
            items.append({"metric": "alloc_low", "text": c.t("x_alloc_low", t=th["low_allocation_pct"])})
        if hq:
            items.append({"metric": "hq", "text": c.t("x_hq", sn=hq["sent_n"], sc=money2(hq["sent_cost"]), rn=hq["recv_n"], rc=money2(hq["recv_cost"]))})
    if scope["kind"] == "month":
        mom = a["mom"]
        if mom["prev_available"]:
            cur_n, cur_c = tot["n"], tot["net"]
            prev = next(m for m in a["months"] if m["period"] == mom["prev"])
            items.append({"metric": "mom", "text": c.t("x_mom", m=_fmt_month(lang, mom["month"]), p=_fmt_month(lang, mom["prev"]), d=f"{cur_n - prev['n']:+,}",
                                                       dp=spct(((cur_n - prev["n"]) / prev["n"] * 100) if prev["n"] else None), dc=smoney(cur_c - prev["net"]),
                                                       dcp=spct(float((cur_c - prev["net"]) / prev["net"] * 100) if prev["net"] else None))})
            if any(m["partial"] for m in a["months"] if m["period"] in (mom["month"], mom["prev"])):
                items.append({"metric": "mom_partial", "text": c.t("i_mom_partial")})
            big = [r["name"] or c.party(r) for r in mom["rows"] if r.get("notable") and r["kind"] == "branch"][:6]
            if big:
                items.append({"metric": "mom_big", "text": c.t("x_mom_big", t=th["mom_change_pct"], names="، ".join(big) if lang == "ar" else ", ".join(big))})
        else:
            items.append({"metric": "prev", "text": c.t("x_prev_missing")})
    for inv in invoices:
        rc = recons.get(inv["id"])
        if rc and not a["filtered"]:
            s = rc["summary"]
            items.append({"metric": "recon", "text": c.t("x_recon_ok", i=inv["invoice_no"] or inv["bill_doc"], n=s["ok"]) if not s["diff"]
                          else c.t("x_recon_diff", i=inv["invoice_no"] or inv["bill_doc"], d=s["diff"])})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    adj_note = None
    if not a["filtered"] and scope["kind"] in ("all", "inv"):
        adj = sum((x["tax"] for rc in recons.values() for x in rc.get("adjustments", [])), Decimal(0))
        inv_total = sum((i["pdf_totals"].get("total", Decimal(0)) for i in invoices), Decimal(0))
        if adj:
            adj_note = c.t("i_adj", lines=money2(tot["gross"]), inv=money2(inv_total), adj=f"{adj:+,.2f}")
    sec.kpis = [{"label": c.t("k_n"), "value": f"{tot['n']:,}", "sub": c.t("ship")},
                {"label": c.t("k_net"), "value": money2(tot["net"]), "sub": c.t("egp")},
                {"label": c.t("k_gross"), "value": money2(tot["gross"]), "sub": c.t("egp")},
                {"label": c.t("k_avg"), "value": money2(tot["avg_net"]) if tot["avg_net"] is not None else "—", "sub": c.t("egp")},
                {"label": c.t("k_branches"), "value": str(tot["branches"]), "sub": ""},
                {"label": c.t("k_conf"), "value": pct(both_pct), "sub": f"{q['both_confirmed_n']:,} / {q['n']:,}", "tone": "up" if both_pct is not None and both_pct < th["low_allocation_pct"] else ""},
                {"label": c.t("k_unalloc"), "value": pct(max((s["unallocated_pct"] or 0) for s in q["sides"].values()) if q["n"] else None), "sub": c.t("sender") + " / " + c.t("receiver")},
                {"label": c.t("k_kg"), "value": f"{tot['kg']:,.2f}", "sub": c.t("kg")}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights.append({"severity": "info", "text": c.t("i_cost")})
    if adj_note:
        sec.insights.append({"severity": "info", "text": adj_note})
    sup = sum(rc["summary"].get("supporting_diff", 0) for rc in recons.values())
    if sup:
        sec.insights.append({"severity": "info", "text": c.t("x_support_diff", n=sup)})
    rm.sections.append(sec)

    # ------------------------------------------------------------ primary table
    sec = ReportSection(c.t("s_branches"), "branches")
    named = branches[: int(th["top_n"])]
    sec.charts.append({"type": "bar", "horizontal": True, "stacked": True, "title": c.t("ch_top"), "x": [p["name"] for p in named], "series": [
        {"name": c.t("c_sent_c"), "values": [float(p["sent_cost"]) for p in named]}, {"name": c.t("c_recv_c"), "values": [float(p["recv_cost"]) for p in named]}]}) if named else None
    sec.charts = [x for x in sec.charts if x]
    rows = [{"branch": c.party(p), "sent_n": p["sent_n"], "sent_c": p["sent_cost"], "recv_n": p["recv_n"], "recv_c": p["recv_cost"], "tot_n": p["total_n"],
             "tot_c": p["total_cost"], "avg": p["avg_cost"]} for p in parties]
    rows.append({"branch": c.t("total"), "sent_n": ctrl["sent_n"], "sent_c": ctrl["sent_cost"], "recv_n": ctrl["recv_n"], "recv_c": ctrl["recv_cost"], "tot_n": None, "tot_c": None, "avg": tot["avg_net"]})
    sec.tables.append({"key": "branch_table", "title": c.t("t_branch"), "columns": [
        col("branch", c.t("c_branch")), col("sent_n", c.t("c_sent_n"), "int"), col("sent_c", c.t("c_sent_c"), "money"), col("recv_n", c.t("c_recv_n"), "int"),
        col("recv_c", c.t("c_recv_c"), "money"), col("tot_n", c.t("c_tot_n"), "int"), col("tot_c", c.t("c_tot_c"), "money"), col("avg", c.t("c_avg"), "money")],
        "rows": rows, "pdf_rows": 60})
    rm.sections.append(sec)

    # ------------------------------------------------------------ monthly
    sec = ReportSection(c.t("s_monthly"), "monthly")
    months = a["months"]
    if months:
        sec.charts.append({"type": "bar", "title": c.t("ch_month"), "x": [_fmt_month(lang, m["period"], True) for m in months], "series": [{"name": c.t("c_net"), "values": [float(m["net"]) for m in months]}]})
        sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [
            col("period", c.t("c_month")), col("n", c.t("c_n"), "int"), col("net", c.t("c_net"), "money"), col("gross", c.t("c_gross"), "money"), col("avg", c.t("c_avg"), "money"),
            col("dn", c.t("c_dn"), "snum"), col("dnp", c.t("c_dnp"), "spct"), col("dc", c.t("c_dc"), "smoney"), col("dcp", c.t("c_dcp"), "spct"), col("note", c.t("c_partial"))],
            "rows": [{"period": _fmt_month(lang, m["period"]), "n": m["n"], "net": m["net"], "gross": m["gross"], "avg": m["avg_net"], "dn": m.get("d_n"), "dnp": m.get("d_n_pct"),
                      "dc": m.get("d_net"), "dcp": m.get("d_net_pct"), "note": c.t("partial") if m["partial"] else ""} for m in months]})
        if any(m["partial"] for m in months):
            sec.insights.append({"severity": "info", "text": c.t("i_partial_all")})
    sec.insights.append({"severity": "info", "text": c.t("i_month")})
    if scope["kind"] == "month":
        mom = a["mom"]
        if mom["prev_available"]:
            sec.tables.append({"key": "mom", "title": c.t("t_mom"), "columns": [
                col("name", c.t("c_branch")), col("cur_n", c.t("c_cur_n"), "int"), col("prev_n", c.t("c_prev_n"), "int"), col("dn", c.t("c_dn"), "snum"), col("dnp", c.t("c_dnp"), "spct"),
                col("cur_c", c.t("c_cur_c"), "money"), col("prev_c", c.t("c_prev_c"), "money"), col("dc", c.t("c_dc"), "smoney"), col("dcp", c.t("c_dcp"), "spct")],
                "rows": [{"name": c.party(r), "cur_n": r["cur_n"], "prev_n": r["prev_n"], "dn": r["d_n"], "dnp": r["d_n_pct"], "cur_c": r["cur_cost"], "prev_c": r["prev_cost"],
                          "dc": r["d_cost"], "dcp": r["d_cost_pct"]} for r in mom["rows"]], "pdf_rows": 60})
        else:
            sec.insights.append({"severity": "info", "text": c.t("prev_missing")})
    elif len(months) >= 2:
        pm = a["party_months"]
        ms = [m["period"] for m in months]
        order = [p for p in parties]
        mc = [col(f"m{i}", _fmt_month(lang, m, True), "int") for i, m in enumerate(ms)]
        sec.tables.append({"key": "pm_n", "title": c.t("t_pm_n"), "columns": [col("name", c.t("c_branch"))] + mc, "rows": [
            {"name": c.party(p), **{f"m{i}": (pm.get(p["key"], {}).get(m) or {}).get("n") for i, m in enumerate(ms)}} for p in order], "pdf_rows": 50})
        sec.tables.append({"key": "pm_c", "title": c.t("t_pm_c"), "columns": [col("name", c.t("c_branch"))] + [col(f"m{i}", _fmt_month(lang, m, True), "money") for i, m in enumerate(ms)], "rows": [
            {"name": c.party(p), **{f"m{i}": (pm.get(p["key"], {}).get(m) or {}).get("cost") for i, m in enumerate(ms)}} for p in order], "pdf_rows": 50})
    rm.sections.append(sec)

    # ------------------------------------------------------------ allocation quality
    sec = ReportSection(c.t("s_alloc"), "allocation")
    sec.insights.append({"severity": "info", "text": c.t("i_alloc")})
    qrows = []
    for side in ("sender", "receiver"):
        sd = q["sides"][side]
        for kind in ("branch", "head_office", "unallocated"):
            k = sd["kinds"].get(kind, {"n": 0, "cost": Decimal(0)})
            qrows.append({"side": c.t(side), "kind": c.t("k_" + kind), "n": k["n"], "cost": k["cost"], "pct": (k["n"] / q["n"] * 100) if q["n"] else None})
    sec.tables.append({"key": "alloc_quality", "title": c.t("t_quality"), "columns": [col("side", c.t("c_side")), col("kind", c.t("c_kind")), col("n", c.t("c_n"), "int"),
                                                                                       col("cost", c.t("c_cost"), "money"), col("pct", c.t("c_share"), "pct")], "rows": qrows})
    rr = [{"side": c.t(side), "reason": c.t("r_" + rs), "n": v["n"], "cost": v["cost"], "pct": (v["n"] / q["n"] * 100) if q["n"] else None}
          for side in ("sender", "receiver") for rs, v in sorted(q["sides"][side]["reasons"].items(), key=lambda kv: -kv[1]["n"])]
    if rr:
        sec.tables.append({"key": "alloc_reasons", "title": c.t("t_reasons"), "columns": [col("side", c.t("c_side")), col("reason", c.t("c_reason")), col("n", c.t("c_n"), "int"),
                                                                                           col("cost", c.t("c_cost"), "money"), col("pct", c.t("c_share"), "pct")], "rows": rr})
    unreg = sorted({n for s in q["sides"].values() for n in s["unregistered"]})
    if unreg:
        sec.tables.append({"key": "unregistered", "title": c.t("t_unreg"), "columns": [col("name", c.t("c_name"))], "rows": [{"name": n} for n in unreg], "pdf_rows": 40})
    rm.sections.append(sec)

    # ------------------------------------------------------------ reconciliation + controls
    sec = ReportSection(c.t("s_recon"), "recon")
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    else:
        sec.tables.append({"key": "agg_control", "title": c.t("t_ctl"), "columns": [col("key", c.t("c_key")), col("val", c.t("c_val"))], "rows": [
            {"key": c.t("mc"), "val": c.t("mc_ok") if ctrl["ok"] else c.t("mc_bad")}, {"key": c.t("dup"), "val": ctrl["duplicate_awb"]}]})
        sec.tables.append({"key": "invoice_control", "title": c.t("t_invctl"), "columns": [
            col("inv", c.t("c_inv")), col("pdf", c.t("c_pdf"), "int"), col("xlsx", c.t("c_xlsx"), "int"), col("stated", c.t("c_stated"), "money"), col("rows", c.t("c_rows"), "money"),
            col("diff", c.t("c_diff"), "smoney")],
            "rows": [{"inv": i["invoice_no"] or i["bill_doc"], "pdf": i["n_pdf"], "xlsx": i["n_xlsx"], "stated": i["pdf_totals"].get("net"), "rows": i["net_rows"],
                      "diff": (i["net_rows"] - i["pdf_totals"]["net"]) if "net" in i["pdf_totals"] else None} for i in invoices]})
        if len(invoices) == 1 and recons.get(invoices[0]["id"]):
            rc = recons[invoices[0]["id"]]
            sec.tables.append({"key": "checks", "title": c.t("t_checks"), "columns": [col("check", c.t("c_check")), col("exp", c.t("c_exp"), "num"), col("inv", c.t("c_inv_v"), "num"),
                                                                                      col("diff", c.t("c_diff"), "snum"), col("status", c.t("c_status")), col("ref", c.t("c_ref"))],
                               "rows": [{"check": c.s.get("ck_" + k["id"], k["id"]), "exp": k["expected"], "inv": k["invoiced"], "diff": k["diff"], "status": c.t("st_" + k["status"]),
                                         "ref": "; ".join(k["refs"])} for k in rc["checks"]]})
        else:
            sec.tables.append({"key": "recon_summary", "title": c.t("t_recon_sum"), "columns": [col("inv", c.t("c_inv")), col("ok", c.t("st_ok"), "int"), col("diff", c.t("st_diff"), "int")],
                               "rows": [{"inv": i["invoice_no"] or i["bill_doc"], "ok": recons[i["id"]]["summary"]["ok"], "diff": recons[i["id"]]["summary"]["diff"]} for i in invoices if i["id"] in recons]})
        if merge_exc:
            sec.tables.append({"key": "merge_exc", "title": c.t("t_merge"), "columns": [col("awb", c.t("c_awb")), col("src", c.t("c_source")), col("net", c.t("c_net"), "money")],
                               "rows": [{"awb": e["awb"], "src": "PDF" if e["code"] == "awb_only_in_pdf" else "Excel", "net": e["net"]} for e in merge_exc], "pdf_rows": 30})
    rm.sections.append(sec)

    # ------------------------------------------------------------ supporting
    s = a["support"]
    sec = ReportSection(c.t("s_support"), "support")
    ccols = [col("key", c.t("c_city")), col("n", c.t("c_n"), "int"), col("net", c.t("c_net"), "money"), col("avg", c.t("c_avg"), "money"), col("share", c.t("c_share"), "pct")]
    for key, title in (("origins", "t_orig"), ("destinations", "t_dest"), ("routes", "t_routes")):
        sec.tables.append({"key": key, "title": c.t(title), "columns": ccols, "rows": [{"key": r["key"], "n": r["n"], "net": r["net"], "avg": r["avg_net"], "share": r["share"]} for r in s[key]]})
    sec.tables.append({"key": "services", "title": c.t("t_serv"), "columns": [col("key", c.t("c_key")), col("n", c.t("c_n"), "int"), col("net", c.t("c_net"), "money"), col("avg", c.t("c_avg"), "money"),
                                                                                col("kg", c.t("c_kg"), "num")],
                       "rows": [{"key": r["key"], "n": r["n"], "net": r["net"], "avg": r["avg_net"], "kg": r["kg"]} for r in s["services"]]})

    def band(w):
        if w["lo"] is None:
            return c.t("band", hi=w["hi"])
        return c.t("band_top", lo=w["lo"]) if w["hi"] is None else c.t("band_mid", lo=w["lo"], hi=w["hi"])
    sec.tables.append({"key": "weights", "title": c.t("t_weight"), "columns": [col("band", c.t("c_band")), col("n", c.t("c_n"), "int"), col("net", c.t("c_net"), "money"),
                                                                                col("avg", c.t("c_avg"), "money"), col("kg", c.t("c_kg"), "num")],
                       "rows": [{"band": band(w), "n": w["n"], "net": w["net"], "avg": w["avg_net"], "kg": w["kg"]} for w in s["weights"]]})
    ch = s["charges"]
    sec.tables.append({"key": "charges", "title": c.t("t_charges"), "columns": [col("key", c.t("c_item")), col("val", c.t("c_val"), "money")], "rows": [
        {"key": "Base charge", "val": ch["base"]}, {"key": "Other charges", "val": ch["other"]}, {"key": c.t("c_net"), "val": ch["net"]}, {"key": "VAT", "val": ch["tax"]}, {"key": c.t("c_gross"), "val": ch["gross"]}]})
    if ch["other_to_base_min"] is not None:
        sec.insights.append({"severity": "info", "text": c.t("i_ratio", lo=f"{ch['other_to_base_min']:.4f}", hi=f"{ch['other_to_base_max']:.4f}", k=ch["other_to_base_distinct"])})
    if s["rate_check"]:
        sec.insights.append({"severity": "warning" if s["rate_check"]["off_card"] else "info", "text": c.t("i_rate_ok", off=s["rate_check"]["off_card"], n=s["rate_check"]["checked"])})
    rm.sections.append(sec)

    # ------------------------------------------------------------ exceptions
    sec = ReportSection(c.t("s_exc"), "exceptions")
    ex = s["exceptions"]
    if "volumetric" in ex:
        sec.insights.append({"severity": "info", "text": c.t("i_volu", n=ex["volumetric"]["n"], kg=f"{s['volumetric_extra_kg']:,.2f}")})
    sec.tables.append({"key": "exc_summary", "title": c.t("t_excsum"), "columns": [col("flag", c.t("c_flag")), col("n", c.t("c_n"), "int"), col("net", c.t("c_net"), "money")],
                       "rows": [{"flag": c.t("ex_" + k), "n": v["n"], "net": v["net"]} for k, v in sorted(ex.items(), key=lambda kv: -kv[1]["n"])]})
    seen, erows = set(), []
    for k in ("cost_outlier", "heavy", "same_city", "rate_off_card", "allocation_conflict", "multi_piece", "weekend", "volumetric"):
        for r in ex.get(k, {}).get("rows", []):
            if r["awb"] in seen or len(erows) >= 60:
                continue
            seen.add(r["awb"])
            erows.append({"awb": r["awb"], "date": r["pickup_on"].isoformat() if r["pickup_on"] else "", "orig": r["origin"], "dest": r["destination"], "kg": r["weight"], "net": r["net"],
                          "flags": ", ".join(c.t("ex_" + f) for f, v in ex.items() if any(x["awb"] == r["awb"] for x in v["rows"]))})
    if erows:
        sec.tables.append({"key": "exc_rows", "title": c.t("t_excrows"), "columns": [col("awb", c.t("c_awb")), col("date", c.t("c_date")), col("orig", c.t("c_orig")), col("dest", c.t("c_dest")),
                                                                                    col("kg", c.t("c_wt"), "num"), col("net", c.t("c_net"), "money"), col("flags", c.t("c_flags"))], "rows": erows, "pdf_rows": 40})
    rm.sections.append(sec)

    # ------------------------------------------------------------ quality
    sec = ReportSection(c.t("s_quality"), "quality")
    sec.insights.append({"severity": "info", "text": c.t("t_na") + ":"})
    sec.insights += [{"severity": "info", "text": c.t("na_" + u)} for u in unsupported]
    sec.tables.append({"key": "sources", "title": c.t("t_sources"), "columns": [col("role", c.t("c_source")), col("file", c.t("c_key")), col("rows", c.t("c_count"), "int")],
                       "rows": [{"role": x["role"], "file": x["file_name"], "rows": x["rows"]} for x in sources]})
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [col("message", c.t("c_issue")), col("severity", c.t("c_sev")), col("count", c.t("c_count"), "int"),
                                                                               col("examples", c.t("c_examples"))],
                       "rows": [{"message": i["message"], "severity": c.t("sev_" + i["severity"]), "count": i["count"], "examples": " | ".join(i["examples"][:4])} for i in issues], "pdf_rows": 25})
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("name", c.t("c_setting")), col("value", c.t("c_val")), col("source", c.t("c_origin"))],
                       "rows": [{"name": k, "value": th[k], "source": th_origin[k]} for k in th] + [
                           {"name": c.t("sets_hq"), "value": f"{settings_note['locations']} / {settings_note['contacts']}", "source": settings_note["origin"]},
                           {"name": c.t("ref_docs"), "value": settings_note["reference_docs"], "source": ""}]})
    rm.sections.append(sec)
    return rm
