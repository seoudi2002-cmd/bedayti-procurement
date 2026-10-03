"""Turns an analysis result into the generic ReportModel (KPI cards, tables, charts, insights, executive summary).

Every sentence of the executive summary is generated from computed metrics (metric ids are kept in meta so each
statement can be traced); no figure is written by hand and nothing is asserted that the file does not support."""
from datetime import datetime, timezone
from decimal import Decimal

from app.core.reporting.base import ReportModel, ReportSection

MONTH_NAMES = {
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

TITLES = {
    "gl_settlement_lines": ("تحليل العهد المؤقتة (قيود التسوية)", "Temporary Custody Analysis (settlement journal)"),
    "monthly_branch_expense": ("تحليل مصروفات العهد — الفروع", "Custody Expense Analysis — Branches"),
    "monthly_custodian_expense": ("تحليل مصروفات العهد — المركز الرئيسي", "Custody Expense Analysis — Head Office"),
}

T = {
    "ar": {
        "report": "تقرير الإدارة", "scope": "النطاق", "source": "الملف المصدر", "generated": "تاريخ الإنشاء",
        "s_summary": "الملخص التنفيذي", "s_trend": "الإنفاق والاتجاه الشهري", "s_cat": "التحليل حسب بند المصروف",
        "s_scope": "المركز الرئيسي مقابل الفروع", "s_branch": "تحليل الفروع", "s_var": "التغيرات والفروق",
        "s_out": "الملاحظات غير المعتادة", "s_quality": "جودة البيانات وتغطية التحليل", "s_holder": "حسب المسؤول عن العهدة (للأدمن فقط)",
        "k_total": "إجمالي الإنفاق", "k_avg": "متوسط الشهر", "k_peak": "أعلى شهر", "k_low": "أقل شهر", "k_change": "آخر شهر مقابل السابق",
        "k_topcat": "أعلى بند", "k_ho": "حصة المركز الرئيسي", "k_topbr": "أعلى فرع", "k_nbr": "أسماء الفروع التي بها إنفاق", "k_out": "ملاحظات غير معتادة",
        "k_lines": "عدد السطور", "egp": "ج.م", "months": "شهور",
        "c_period": "الفترة", "c_total": "الإجمالي", "c_mom": "التغير عن الشهر السابق", "c_mom_pct": "التغير %", "c_rank": "الترتيب",
        "c_cat": "بند المصروف", "c_label": "التسمية في الملف", "c_share": "النسبة %", "c_cum": "التراكمي %", "c_lines": "السطور",
        "c_branch": "الفرع", "c_months": "شهور بها إنفاق", "c_ho": "المركز الرئيسي", "c_br": "الفروع", "c_item": "البند الفرعي",
        "c_prev": "السابق", "c_cur": "الحالي", "c_abs": "الفرق", "c_sev": "الأهمية", "c_note": "الملاحظة", "c_val": "القيمة",
        "c_base": "المرجع", "c_stated": "المذكور في الملف", "c_computed": "المحسوب", "c_diff": "الفرق", "c_status": "الحالة",
        "c_ref": "المرجع في الملف", "c_issue": "الملاحظة", "c_count": "العدد", "c_examples": "أمثلة", "c_name": "الإعداد",
        "c_source": "المصدر", "c_group": "المجموعة", "c_members": "البنود", "c_holder": "المسؤول", "c_kind": "النوع",
        "c_avg": "المتوسط", "c_median": "الوسيط", "c_stat": "المؤشر", "c_basis": "الأساس",
        "t_months": "الإنفاق الشهري", "t_cat": "الإنفاق حسب البند", "t_catm": "البند × الشهر", "t_item": "البنود الفرعية",
        "t_scope": "المركز الرئيسي مقابل الفروع حسب الشهر", "t_scopec": "المركز الرئيسي مقابل الفروع حسب البند",
        "t_branch": "ترتيب الفروع", "t_group": "مجموعات الفروع (غير موزعة على فروع)", "t_matrix": "الفرع × البند (الأعلى)",
        "t_stats": "مقارنة الفروع — إحصاءات", "t_varc": "التغير حسب البند", "t_varb": "التغير حسب الفرع", "t_out": "الملاحظات غير المعتادة",
        "t_ctrl": "مطابقة الإجماليات مع الملف", "t_issues": "ملاحظات جودة البيانات", "t_set": "الإعدادات المستخدمة",
        "t_groups": "مقترح تجميع للعرض (بانتظار الاعتماد — الأسماء الأصلية لم تتغير)", "t_holder": "الإنفاق حسب المسؤول",
        "t_grouped": "الإنفاق حسب مجموعة العرض المعتمدة",
        "ch_trend": "الإنفاق الشهري", "ch_pareto": "البنود (الأعلى إلى الأقل) والنسبة التراكمية", "ch_heat": "خريطة حرارية: البند × الشهر",
        "ch_scope": "المركز الرئيسي مقابل الفروع", "ch_top": "أعلى الفروع إنفاقًا", "ch_bheat": "خريطة حرارية: الفرع × البند",
        "ch_wf": "ما الذي غيّر الإجمالي بين الشهرين؟", "ch_dist": "توزيع إنفاق الفروع",
        "sev_critical": "حرج", "sev_warning": "تنبيه", "sev_info": "للعلم", "ok": "مطابق", "diff": "فرق", "no_stated": "لا يوجد إجمالي في الملف",
        "ho": "المركز الرئيسي", "br": "الفروع", "total": "الإجمالي", "st_total": "الإجمالي", "st_category": "بند", "st_branch": "فرع",
        "st_scope": "نطاق", "unsupported_head": "غير مدعوم بهذا الملف (لم تُحسب أي أرقام بديلة):",
        "un_head_office_vs_branches": "المقارنة بين المركز الرئيسي والفروع", "un_branch": "التحليل حسب الفرع",
        "un_branch_comparison": "مقارنة فرع بفرع", "un_top_branches": "أعلى الفروع", "un_branch_by_category": "الفرع × البند",
        "un_month": "التحليل الشهري", "un_category": "التحليل حسب البند",
        "r_mom_change": "{who}: تغير من {baseline} إلى {value} في {period} ({abs}, {pct}).",
        "r_new_in_period": "{who}: ظهر إنفاق جديد بقيمة {value} في {period} (لم يكن هناك إنفاق في الشهر السابق).",
        "r_month_vs_average": "إجمالي {period} ({value}) يختلف بنسبة {pct} عن متوسط باقي الشهور ({baseline}){ind}.",
        "r_branch_above_fence": "إجمالي الفرع «{subject}» ({value}) أعلى من الحد الإحصائي لباقي الفروع ({baseline}).",
        "r_dominant_line": "سطر واحد بقيمة {value} يمثل {pct} من إجمالي بند «{subject}» ({ref}).",
        "r_repeated_amount": "المبلغ {value} تكرر {count} مرات في بند «{subject}» ({refs}).",
        "r_negative_amount": "مبلغ سالب {value} في بند «{subject}» — محفوظ كما ورد ({ref}).",
        "r_reclass_entry": "قيد إعادة تبويب يدوي بمبلغ {value} في بند «{subject}» — محفوظ كما ورد ({ref}).",
        "r_branches_start_spending": "{count} فرعًا بدأ إنفاقها بعد الشهر الأول للملف (أعلاها: {subject}).",
        "r_branches_stop_spending": "{count} فرعًا بلا إنفاق في آخر شهر رغم إنفاق سابق (أعلاها: {subject}).",
        "ind": " (استرشادي: عدد الشهور قليل)",
        "i_facts_without_month": "{count} سطر بقيمة {amount} بلا شهر؛ داخل الإجمالي وخارج التحليل الشهري.",
        "i_scope_unspecified": "مبلغ {amount} بلا تحديد (مركز رئيسي/فروع) ولم يُنسب لأي منهما.",
        "i_year_unknown": "السنة غير مذكورة في الملف؛ تُعرض الشهور بدون سنة.",
        "i_year_uploader": "السنة ({year}) أُدخلت عند الرفع وليست من الملف.",
        "i_thr_default": "حدود الملاحظات غير المعتادة هي القيم الابتدائية ولم تُعتمد بعد؛ يمكن تعديلها من إعدادات النظام.",
        "i_ctrl_diff": "{n} من إجماليات الملف لا تطابق ما حُسب من البيانات (التفاصيل في جدول المطابقة).",
        "i_ctrl_ok": "كل إجماليات الملف تطابق ما حُسب من البيانات.",
        "i_ctrl_none": "لا يحتوي الملف على إجماليات يمكن مطابقتها.",
        "i_indicative": "عدد الشهور ({n}) قليل؛ تعد قراءة الاتجاه استرشادية.",
        "i_branch_names": "شهور ({p}) تستخدم أسماء فروع مختلفة عن باقي الشهور (مثل لغة الاسم)؛ استُبعدت من اختبارات التغير على مستوى الفرع، وتظهر أسماؤها كفروع منفصلة حتى تُربط بسجل الفروع.",
        "i_category_variants": "بنود ظهرت بتسميات مختلفة في الملف ({v}); لم تُدمج ولم تُقارن شهريًا (انظر مقترح التجميع للاعتماد).",
        "other": "أخرى", "k_findings": "أهم الملاحظات", "f_period": "الفترة", "f_branch": "الفرع", "f_category": "البند", "f_filtered": "عرض مفلتر",
        "i_filtered": "العرض الحالي مفلتر؛ مطابقة إجماليات الملف تخص الملف كله ولا تُعرض مع الفلاتر.",
        "x_total": "بلغ إجمالي الإنفاق {total} ج.م خلال {n} شهر ({span})، بمتوسط شهري {avg} ج.م.",
        "x_total_nomonth": "بلغ إجمالي الإنفاق {total} ج.م (الملف لا يحدد الشهور).",
        "x_topcats": "أعلى بند هو «{c1}» بنسبة {p1} من الإجمالي{more}؛ وأعلى {k} بنود تمثل {cum}.",
        "x_more": "، يليه «{c2}» ({p2})",
        "x_scope": "المركز الرئيسي يمثل {pho} من الإجمالي ({ho} ج.م) والفروع {pbr} ({br} ج.م).",
        "x_branches": "أعلى فرع إنفاقًا «{b1}» بقيمة {v1} ج.م ({p1} من الإجمالي)؛ وأعلى 5 فروع تمثل {top5} من إنفاق الفروع.",
        "x_peak": "أعلى شهر {pk} ({vk} ج.م) وأقل شهر {lk} ({vl} ج.م).",
        "x_change": "إجمالي {to} مقابل {frm}: {abs} ج.م ({pct}). أكبر بند تغيرًا: «{c}» ({cabs} ج.م).",
        "x_out": "رُصدت {n} ملاحظة غير معتادة وفق الحدود المعتمدة في الإعدادات (أهمها في قسم الملاحظات).",
        "k_caveats": "تحفظات وحدود",
    },
    "en": {
        "report": "Management report", "scope": "Scope", "source": "Source file", "generated": "Generated",
        "s_summary": "Executive summary", "s_trend": "Spend and monthly trend", "s_cat": "Analysis by expense category",
        "s_scope": "Head Office vs branches", "s_branch": "Branch analysis", "s_var": "Changes and variances",
        "s_out": "Unusual items", "s_quality": "Data quality and analysis coverage", "s_holder": "By custodian (admin only)",
        "k_total": "Total expenditure", "k_avg": "Monthly average", "k_peak": "Peak month", "k_low": "Lowest month",
        "k_change": "Latest month vs previous", "k_topcat": "Top category", "k_ho": "Head Office share", "k_topbr": "Top branch",
        "k_nbr": "Branch names with spend", "k_out": "Unusual items", "k_lines": "Source lines", "egp": "EGP", "months": "months",
        "c_period": "Period", "c_total": "Total", "c_mom": "Change vs previous month", "c_mom_pct": "Change %", "c_rank": "Rank",
        "c_cat": "Expense category", "c_label": "Label in file", "c_share": "Share %", "c_cum": "Cumulative %", "c_lines": "Lines",
        "c_branch": "Branch", "c_months": "Months with spend", "c_ho": "Head Office", "c_br": "Branches", "c_item": "Sub-item",
        "c_prev": "Previous", "c_cur": "Current", "c_abs": "Change", "c_sev": "Severity", "c_note": "Observation", "c_val": "Value",
        "c_base": "Baseline", "c_stated": "Stated in file", "c_computed": "Computed", "c_diff": "Difference", "c_status": "Status",
        "c_ref": "Source reference", "c_issue": "Observation", "c_count": "Count", "c_examples": "Examples", "c_name": "Setting",
        "c_source": "Source", "c_group": "Group", "c_members": "Categories", "c_holder": "Custodian", "c_kind": "Type",
        "c_avg": "Average", "c_median": "Median", "c_stat": "Metric", "c_basis": "Basis",
        "t_months": "Monthly expenditure", "t_cat": "Expenditure by category", "t_catm": "Category × month", "t_item": "Sub-items",
        "t_scope": "Head Office vs branches by month", "t_scopec": "Head Office vs branches by category",
        "t_branch": "Branch ranking", "t_group": "Branch groups (not allocated to individual branches)", "t_matrix": "Branch × category (top)",
        "t_stats": "Branch comparison statistics", "t_varc": "Change by category", "t_varb": "Change by branch", "t_out": "Unusual items",
        "t_ctrl": "Control totals against the file", "t_issues": "Data-quality observations", "t_set": "Settings used",
        "t_groups": "Suggested display grouping (awaiting approval — original names unchanged)", "t_holder": "Expenditure by custodian",
        "t_grouped": "Expenditure by approved display group",
        "ch_trend": "Monthly expenditure", "ch_pareto": "Categories (high to low) and cumulative share", "ch_heat": "Heatmap: category × month",
        "ch_scope": "Head Office vs branches", "ch_top": "Top branches by expenditure", "ch_bheat": "Heatmap: branch × category",
        "ch_wf": "What changed the total between the two months?", "ch_dist": "Distribution of branch spend",
        "sev_critical": "Critical", "sev_warning": "Warning", "sev_info": "Info", "ok": "Matches", "diff": "Differs", "no_stated": "No total in file",
        "ho": "Head Office", "br": "Branches", "total": "Total", "st_total": "Total", "st_category": "Category", "st_branch": "Branch",
        "st_scope": "Scope", "unsupported_head": "Not supported by this file (no substitute figures were calculated):",
        "un_head_office_vs_branches": "Head Office vs branches comparison", "un_branch": "Analysis by branch",
        "un_branch_comparison": "Branch-to-branch comparison", "un_top_branches": "Top branches", "un_branch_by_category": "Branch × category",
        "un_month": "Monthly analysis", "un_category": "Analysis by category",
        "r_mom_change": "{who}: moved from {baseline} to {value} in {period} ({abs}, {pct}).",
        "r_new_in_period": "{who}: new spend of {value} in {period} (none in the previous month).",
        "r_month_vs_average": "{period} total ({value}) is {pct} versus the average of the other months ({baseline}){ind}.",
        "r_branch_above_fence": "Branch “{subject}” total ({value}) is above the statistical fence for the other branches ({baseline}).",
        "r_dominant_line": "A single line of {value} is {pct} of category “{subject}” ({ref}).",
        "r_repeated_amount": "Amount {value} repeated {count} times in category “{subject}” ({refs}).",
        "r_negative_amount": "Negative amount {value} in category “{subject}” — kept as written ({ref}).",
        "r_reclass_entry": "Manual reclassification entry of {value} in category “{subject}” — kept as written ({ref}).",
        "r_branches_start_spending": "{count} branches began spending after the file's first period (largest: {subject}).",
        "r_branches_stop_spending": "{count} branches have no spend in the last period despite earlier spend (largest: {subject}).",
        "ind": " (indicative: few months)",
        "i_facts_without_month": "{count} lines worth {amount} have no month; included in the total, excluded from monthly analysis.",
        "i_scope_unspecified": "{amount} has no Head Office/branch designation and is attributed to neither.",
        "i_year_unknown": "The year is not stated in the file; months are shown without a year.",
        "i_year_uploader": "The year ({year}) was supplied at upload, not read from the file.",
        "i_thr_default": "Unusual-item thresholds are still the initial values and not yet confirmed; adjust them in system settings.",
        "i_ctrl_diff": "{n} of the file's own totals do not match what the data adds up to (see the control table).",
        "i_ctrl_ok": "All totals stated in the file match what the data adds up to.",
        "i_ctrl_none": "The file has no totals that can be checked.",
        "i_indicative": "Only {n} months of data: trend readings are indicative.",
        "i_branch_names": "Periods ({p}) use different branch names from the other periods (e.g. another language); they are excluded from branch-level change tests and their names appear as separate branches until mapped to the branch master.",
        "i_category_variants": "Categories written differently in the file ({v}) were not merged and not compared month to month (see the suggested grouping for approval).",
        "other": "Other", "k_findings": "Key observations", "f_period": "Period", "f_branch": "Branch", "f_category": "Category", "f_filtered": "Filtered view",
        "i_filtered": "This view is filtered; the file's own control totals refer to the whole file and are not shown with filters.",
        "x_total": "Total expenditure was EGP {total} over {n} months ({span}), an average of EGP {avg} per month.",
        "x_total_nomonth": "Total expenditure was EGP {total} (the file does not state months).",
        "x_topcats": "The largest category is “{c1}” at {p1} of the total{more}; the top {k} categories make up {cum}.",
        "x_more": ", followed by “{c2}” ({p2})",
        "x_scope": "Head Office accounts for {pho} of the total (EGP {ho}) and branches {pbr} (EGP {br}).",
        "x_branches": "The highest-spending branch is “{b1}” at EGP {v1} ({p1} of the total); the top 5 branches are {top5} of branch spend.",
        "x_peak": "The peak month is {pk} (EGP {vk}) and the lowest is {lk} (EGP {vl}).",
        "x_change": "{to} versus {frm}: EGP {abs} ({pct}). Largest mover: “{c}” (EGP {cabs}).",
        "x_out": "{n} unusual items were flagged against the thresholds in system settings (the most significant are listed in the unusual-items section).",
        "k_caveats": "Caveats and limits",
    },
}


def money(v) -> str:
    return f"{Decimal(v):,.0f}"


def pct(v) -> str:
    return "—" if v is None else f"{v:.1f}%"


def spct(v) -> str:
    return "—" if v is None else f"{v:+.1f}%"


def smoney(v) -> str:
    return f"{Decimal(v):+,.0f}"


class Ctx:
    def __init__(self, lang: str, year: int | None):
        self.lang, self.year, self.s = lang, year, T[lang]

    def t(self, key: str, **kw) -> str:
        return self.s[key].format(**kw) if kw else self.s[key]

    def period(self, k) -> str:
        y, m = k
        name = MONTH_NAMES[self.lang][m - 1]
        return f"{name} {y}" if y else (f"{name} {self.year}" if self.year else name)

    def short(self, k) -> str:
        y, m = k
        return MONTH_NAMES[self.lang][m - 1] + (f" {str(y or self.year)[2:]}" if (y or self.year) else "")


def col(key, label, fmt="text"):
    return {"key": key, "label": label, "fmt": fmt}


def build_report(dataset, a: dict, lang: str = "ar", admin: bool = False, taxonomy: dict | None = None,
                 holder_rows: list[dict] | None = None, filters: dict | None = None, options: dict | None = None) -> ReportModel:
    c = Ctx(lang, dataset.period_year)
    periods = [p["key"] for p in a["periods"]]
    summ = dataset.summary
    labels = summ.get("labels", {})
    cap = a["capabilities"]
    title = TITLES.get(dataset.layout, (dataset.layout, dataset.layout))[0 if lang == "ar" else 1]
    span = f"{c.period(periods[0])} – {c.period(periods[-1])}" if periods else ""
    rm = ReportModel(title=title, period_label=span, sections=[], lang=lang)
    rm.subtitle = f"{c.t('source')}: {dataset.file_name}"
    rm.meta = {"dataset_id": dataset.id, "file_name": dataset.file_name, "file_hash": dataset.file_hash, "layout": dataset.layout,
               "scope_label": dataset.scope_label, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
               "year": dataset.period_year, "year_source": dataset.year_source}

    filters = filters or {}
    rm.meta["filters"] = {"active": filters, "options": options or {}}
    if filters:
        sel = []
        if filters.get("periods"):
            sel.append(f"{c.t('f_period')}: " + ", ".join(
                o["label"] for o in (options or {}).get("periods", []) if o["id"] in filters["periods"]))
        if filters.get("branches"):
            sel.append(f"{c.t('f_branch')}: " + ", ".join(
                o["label"] for o in (options or {}).get("branches", []) if o["key"] in filters["branches"]))
        if filters.get("categories"):
            sel.append(f"{c.t('f_category')}: " + ", ".join(filters["categories"]))
        rm.subtitle = (rm.subtitle or "") + " · " + c.t("f_filtered") + " — " + " | ".join(sel)

    # ------------------------------------------------------------------ quality inputs (used by the summary too)
    controls = [] if filters else summ.get("controls", [])
    bad_ctrl = [x for x in controls if x["stated"] is None or abs(x["stated"] - x["computed"]) > 0.5]
    caveats: list[str] = []
    if cap["month"] and not cap["year"] and dataset.period_year is None:
        caveats.append(c.t("i_year_unknown"))
    if dataset.year_source == "uploader":
        caveats.append(c.t("i_year_uploader", year=dataset.period_year))
    if a["period_stats"] if a.get("period_stats") and a["period_stats"]["indicative"] else False:
        caveats.append(c.t("i_indicative", n=a["n_periods"]))
    if filters:
        caveats.append(c.t("i_filtered"))
    elif bad_ctrl:
        caveats.append(c.t("i_ctrl_diff", n=len(bad_ctrl)))
    elif controls:
        caveats.append(c.t("i_ctrl_ok"))
    else:
        caveats.append(c.t("i_ctrl_none"))
    if a.get("branch_name_inconsistent_periods"):
        caveats.append(c.t("i_branch_names", p=", ".join(c.period(k) for k in a["branch_name_inconsistent_periods"])))
    if a.get("category_variants"):
        caveats.append(c.t("i_category_variants", v="؛ ".join(" / ".join(g) for g in a["category_variants"][:4])))
    if all(v == "default" for v in a["thresholds_origin"].values()):
        caveats.append(c.t("i_thr_default"))
    for n in a["notes"]:
        caveats.append(c.t("i_" + n["code"], count=n.get("count", ""), amount=money(n.get("amount", 0))))

    # ------------------------------------------------------------------ 1. summary
    items: list[dict] = []

    def say(metric: str, text: str):
        items.append({"metric": metric, "text": text})

    ps = a.get("period_stats")
    if ps:
        say("total", c.t("x_total", total=money(a["total"]), n=a["n_periods"], span=span, avg=money(ps["avg"])))
    else:
        say("total", c.t("x_total_nomonth", total=money(a["total"])))
    cats = a["by_category"]
    if cats:
        k = min(3, len(cats))
        more = c.t("x_more", c2=cats[1]["name"], p2=pct(cats[1]["share"])) if len(cats) > 1 else ""
        say("top_category", c.t("x_topcats", c1=cats[0]["name"], p1=pct(cats[0]["share"]), more=more, k=k, cum=pct(cats[k - 1]["cum_share"])))
    if a.get("by_scope"):
        s = a["by_scope"]
        say("head_office_share", c.t("x_scope", pho=pct(s["head_office"]["share"]), ho=money(s["head_office"]["total"]),
                                     pbr=pct(s["branch"]["share"]), br=money(s["branch"]["total"])))
    if a.get("by_branch"):
        b = a["by_branch"][0]
        say("top_branch", c.t("x_branches", b1=b["name"], v1=money(b["total"]), p1=pct(b["share_of_all"]),
                              top5=pct((a.get("branch_stats") or {}).get("top5_share"))))
    if ps and a["n_periods"] > 1:
        say("peak_month", c.t("x_peak", pk=c.period(ps["max_key"]), vk=money(ps["max"]), lk=c.period(ps["min_key"]), vl=money(ps["min"])))
    v = a.get("variance")
    if v and v["by_category"]:
        top = v["by_category"][0]
        say("last_vs_prev", c.t("x_change", to=c.period(v["to"]), frm=c.period(v["from"]), abs=smoney(v["total"]["abs"]),
                                pct=spct(v["total"]["pct"]), c=top["name"], cabs=smoney(top["abs"])))
    if a["outliers"]:
        say("n_outliers", c.t("x_out", n=len(a["outliers"])))
    for cv in caveats:
        items.append({"metric": "caveat", "text": cv})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items

    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = _kpis(a, c)
    sec.insights = [{"severity": "info" if i["metric"] != "caveat" else "warning", "text": i["text"], "metric": i["metric"]}
                    for i in items]
    pool = [o for o in a["outliers"] if o["severity"] != "info"] or a["outliers"]
    top_out, totals = [], 0
    for o in pool:  # a spread of findings, not five movements of the grand total
        if o["subject_type"] == "total":
            totals += 1
            if totals > 2:
                continue
        top_out.append(o)
        if len(top_out) == 5:
            break
    for o in top_out:
        sec.insights.append({"severity": o["severity"], "text": _outlier_text(c, o), "metric": "outlier"})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 2. trend
    sec = ReportSection(c.t("s_trend"), "trend")
    if periods:
        x = [c.short(k) for k in periods]
        sec.charts.append({"type": "bar", "title": c.t("ch_trend"), "x": x,
                           "series": [{"name": c.t("c_total"), "values": [float(p["total"]) for p in a["periods"]]}]})
        sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [
            col("period", c.t("c_period")), col("total", c.t("c_total"), "money"), col("mom", c.t("c_mom"), "smoney"),
            col("mom_pct", c.t("c_mom_pct"), "spct")], "rows": [
            {"period": c.period(p["key"]), "total": p["total"], "mom": p["mom_abs"], "mom_pct": p["mom_pct"]} for p in a["periods"]]})
        if a.get("by_scope"):
            s = a["by_scope"]
            sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_scope"), "x": x, "series": [
                {"name": c.t("ho"), "values": [float(s["head_office"]["by_month"].get(k, 0)) for k in periods]},
                {"name": c.t("br"), "values": [float(s["branch"]["by_month"].get(k, 0)) for k in periods]}]})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_month")})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 3. categories
    sec = ReportSection(c.t("s_cat"), "categories")
    if cats:
        top = cats[: int(a["thresholds"]["top_n"]) + 5]
        sec.charts.append({"type": "pareto", "drill": "category", "title": c.t("ch_pareto"), "x": [r["name"] for r in top],
                           "values": [float(r["total"]) for r in top], "cum": [r["cum_share"] for r in top]})
        sec.tables.append({"key": "categories", "title": c.t("t_cat"), "columns": [
            col("rank", c.t("c_rank"), "int"), col("name", c.t("c_cat")), col("label", c.t("c_label")),
            col("total", c.t("c_total"), "money"), col("share", c.t("c_share"), "pct"), col("cum", c.t("c_cum"), "pct"),
            col("lines", c.t("c_lines"), "int")], "rows": [
            {"rank": r["rank"], "name": r["name"], "label": labels.get(r["name"], ""), "total": r["total"], "share": r["share"],
             "cum": r["cum_share"], "lines": r["n_lines"]} for r in cats]})
        if periods and len(periods) > 1:
            mc = cats[:12]
            sec.charts.append({"type": "heatmap", "drill_rows": "category", "title": c.t("ch_heat"), "rows": [r["name"] for r in mc],
                               "cols": [c.short(k) for k in periods],
                               "values": [[float(r["by_month"].get(k, 0)) or None for k in periods] for r in mc]})
            sec.tables.append({"key": "category_month", "title": c.t("t_catm"), "columns": [col("name", c.t("c_cat"))] + [
                col(f"p{i}", c.short(k), "money") for i, k in enumerate(periods)] + [col("total", c.t("c_total"), "money")],
                "rows": [{"name": r["name"], **{f"p{i}": r["by_month"].get(k) for i, k in enumerate(periods)}, "total": r["total"]}
                         for r in cats], "pdf_rows": 14})
        if a["by_item"]:
            sec.tables.append({"key": "items", "title": c.t("t_item"), "columns": [
                col("category", c.t("c_cat")), col("item", c.t("c_item")), col("total", c.t("c_total"), "money"),
                col("share", c.t("c_share"), "pct")], "rows": a["by_item"], "pdf_rows": 15})
        groups = (taxonomy or {}).get("groups") or {}
        if groups:
            tot_by = {r["name"]: r["total"] for r in cats}
            rows, used = [], set()
            for g, members in groups.items():
                mem = [m for m in members if m in tot_by]
                used.update(mem)
                if mem:
                    t_ = sum((tot_by[m] for m in mem), Decimal("0"))
                    rows.append({"group": g, "members": " + ".join(mem), "total": t_, "share": float(t_ / a["total"] * 100) if a["total"] else None})
            for m, t_ in tot_by.items():
                if m not in used:
                    rows.append({"group": m, "members": "", "total": t_, "share": float(t_ / a["total"] * 100) if a["total"] else None})
            rows.sort(key=lambda r: r["total"], reverse=True)
            sec.tables.append({"key": "grouped", "title": c.t("t_grouped"), "columns": [
                col("group", c.t("c_group")), col("members", c.t("c_members")), col("total", c.t("c_total"), "money"),
                col("share", c.t("c_share"), "pct")], "rows": rows})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_category")})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 4. head office vs branches
    sec = ReportSection(c.t("s_scope"), "scope")
    if a.get("by_scope"):
        s = a["by_scope"]
        sec.tables.append({"key": "scope_month", "title": c.t("t_scope"), "columns": [
            col("period", c.t("c_period")), col("ho", c.t("c_ho"), "money"), col("br", c.t("c_br"), "money"),
            col("total", c.t("c_total"), "money"), col("ho_pct", c.t("c_ho") + " %", "pct")], "rows": [
            {"period": c.period(k), "ho": s["head_office"]["by_month"].get(k, Decimal(0)), "br": s["branch"]["by_month"].get(k, Decimal(0)),
             "total": s["head_office"]["by_month"].get(k, Decimal(0)) + s["branch"]["by_month"].get(k, Decimal(0)),
             "ho_pct": _share(s["head_office"]["by_month"].get(k, Decimal(0)), s["branch"]["by_month"].get(k, Decimal(0)))}
            for k in periods]})
        cn = sorted({*s["head_office"]["by_category"], *s["branch"]["by_category"]},
                    key=lambda n: -(s["head_office"]["by_category"].get(n, 0) + s["branch"]["by_category"].get(n, 0)))
        sec.tables.append({"key": "scope_category", "title": c.t("t_scopec"), "columns": [
            col("name", c.t("c_cat")), col("ho", c.t("c_ho"), "money"), col("br", c.t("c_br"), "money"),
            col("ho_pct", c.t("c_ho") + " %", "pct")], "rows": [
            {"name": n, "ho": s["head_office"]["by_category"].get(n), "br": s["branch"]["by_category"].get(n),
             "ho_pct": _share(s["head_office"]["by_category"].get(n, Decimal(0)), s["branch"]["by_category"].get(n, Decimal(0)))} for n in cn]})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_head_office_vs_branches")})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 5. branches
    sec = ReportSection(c.t("s_branch"), "branches")
    brs = a.get("by_branch", [])
    if brs:
        n = int(a["thresholds"]["top_n"])
        sec.charts.append({"type": "bar", "horizontal": True, "drill": "branch", "title": c.t("ch_top"), "x": [r["name"] for r in brs[:n]],
                           "series": [{"name": c.t("c_total"), "values": [float(r["total"]) for r in brs[:n]]}]})
        sec.tables.append({"key": "branches", "title": c.t("t_branch"), "columns": [
            col("rank", c.t("c_rank"), "int"), col("name", c.t("c_branch")), col("total", c.t("c_total"), "money"),
            col("share", c.t("c_share"), "pct"), col("cum", c.t("c_cum"), "pct"), col("months", c.t("c_months"), "int")], "rows": [
            {"rank": r["rank"], "name": r["name"], "total": r["total"], "share": r["share_of_group"], "cum": r["cum_share"],
             "months": r["months_active"]} for r in brs], "pdf_rows": 20})
        bm = a["branch_category_matrix"]
        if bm["rows"] and bm["categories"]:
            sec.charts.append({"type": "heatmap", "drill_rows": "branch", "drill_cols": "category", "title": c.t("ch_bheat"), "rows": [r["name"] for r in bm["rows"]], "cols": bm["categories"],
                               "values": [[float(x) if x else None for x in r["cells"]] for r in bm["rows"]]})
            sec.tables.append({"key": "branch_category", "title": c.t("t_matrix"), "columns": [col("name", c.t("c_branch"))] + [
                col(f"c{i}", cn_, "money") for i, cn_ in enumerate(bm["categories"])] + [col("total", c.t("c_total"), "money")],
                "rows": [{"name": r["name"], **{f"c{i}": x for i, x in enumerate(r["cells"])}, "total": r["total"]} for r in bm["rows"]],
                "pdf_rows": 12, "pdf_cols": 5})
        st = a.get("branch_stats")
        if st:
            sec.tables.append({"key": "branch_stats", "title": c.t("t_stats"), "columns": [col("stat", c.t("c_stat")), col("value", c.t("c_val"))],
                               "rows": [{"stat": k_, "value": v_} for k_, v_ in [
                                   (c.t("k_nbr"), str(st["count"])), (c.t("c_avg"), money(st["mean"])), (c.t("c_median"), money(st["median"])),
                                   ("P90", money(st["p90"]) if st["p90"] is not None else "—"),
                                   ("max", money(st["max"])), ("min", money(st["min"])), ("Top 5 %", pct(st["top5_share"])),
                                   ("Top 10 %", pct(st["top10_share"]))]]})
    elif not cap["branch"]:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + " / ".join(c.t(u) for u in (
            "un_branch", "un_top_branches", "un_branch_comparison", "un_branch_by_category"))})
    if a.get("by_group"):
        sec.tables.append({"key": "groups", "title": c.t("t_group"), "columns": [
            col("name", c.t("c_branch")), col("total", c.t("c_total"), "money"), col("share", c.t("c_share"), "pct")],
            "rows": [{"name": r["name"], "total": r["total"], "share": r["share_of_all"]} for r in a["by_group"]]})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 6. variance
    sec = ReportSection(c.t("s_var"), "variance")
    if v:
        top = v["by_category"][:8]
        sec.charts.append({"type": "waterfall", "title": f"{c.t('ch_wf')} ({c.short(v['from'])} → {c.short(v['to'])})",
                           "start": (c.short(v["from"]), float(v["total"]["prev"])), "end": (c.short(v["to"]), float(v["total"]["cur"])),
                           "x": [r["name"] for r in top], "values": [float(r["abs"]) for r in top],
                           "other_label": c.t("other"), "other": float(v["total"]["abs"] - sum((r["abs"] for r in top), Decimal(0)))})
        cols = [col("name", ""), col("prev", c.short(v["from"]), "money"), col("cur", c.short(v["to"]), "money"),
                col("abs", c.t("c_abs"), "smoney"), col("pct", c.t("c_mom_pct"), "spct")]
        sec.tables.append({"key": "var_category", "title": c.t("t_varc"), "columns": [{**cols[0], "label": c.t("c_cat")}] + cols[1:],
                           "rows": v["by_category"], "pdf_rows": 12})
        if v["by_branch"]:
            sec.tables.append({"key": "var_branch", "title": c.t("t_varb"), "columns": [{**cols[0], "label": c.t("c_branch")}] + cols[1:],
                               "rows": v["by_branch"], "pdf_rows": 12})
    else:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + c.t("un_month")})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 7. outliers
    sec = ReportSection(c.t("s_out"), "outliers")
    rows = []
    for o in a["outliers"]:
        rows.append({"sev": c.t("sev_" + o["severity"]), "note": _outlier_text(c, o), "period": c.period(o["period"]) if o["period"] else "",
                     "value": o["value"], "baseline": o["baseline"],
                     "ref": ", ".join(o.get("refs", [])[:3])})
    sec.tables.append({"key": "outliers", "title": c.t("t_out"), "columns": [
        col("sev", c.t("c_sev")), col("note", c.t("c_note")), col("period", c.t("c_period")), col("value", c.t("c_val"), "money"),
        col("baseline", c.t("c_base"), "money"), col("ref", c.t("c_ref"))], "rows": rows, "pdf_rows": 25})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 8. quality
    sec = ReportSection(c.t("s_quality"), "quality")
    sec.insights += [{"severity": "info", "text": x} for x in caveats]
    unsupported = [u for u in a["unsupported"]]
    if unsupported:
        sec.insights.append({"severity": "info", "text": c.t("unsupported_head") + " " + ", ".join(
            c.s.get("un_" + u, u) for u in unsupported)})
    sec.tables.append({"key": "controls", "title": c.t("t_ctrl"), "columns": [
        col("label", c.t("c_note")), col("period", c.t("c_period")), col("stated", c.t("c_stated"), "money"),
        col("computed", c.t("c_computed"), "money"), col("diff", c.t("c_diff"), "smoney"), col("status", c.t("c_status")),
        col("ref", c.t("c_ref"))], "rows": [{
            "label": x["label"], "period": c.period((dataset.period_year or 0, x["month"])) if x["month"] else "",
            "stated": x["stated"], "computed": x["computed"],
            "diff": None if x["stated"] is None else round(x["computed"] - x["stated"], 2),
            "status": c.t("no_stated") if x["stated"] is None else (c.t("ok") if abs(x["computed"] - x["stated"]) <= 0.5 else c.t("diff")),
            "ref": x["source_ref"]} for x in controls]})
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [
        col("message", c.t("c_issue")), col("severity", c.t("c_sev")), col("count", c.t("c_count"), "int"), col("examples", c.t("c_examples"))],
        "rows": [{"message": i["message"], "severity": c.t("sev_" + i["severity"]), "count": i["count"],
                  "examples": " | ".join(i["examples"][:4])} for i in summ.get("issues", [])], "pdf_rows": 20})
    sg = summ.get("suggested_groups", [])
    if sg:
        sec.tables.append({"key": "suggested_groups", "title": c.t("t_groups"), "columns": [
            col("label", c.t("c_group")), col("members", c.t("c_members")), col("basis", c.t("c_basis"))],
            "rows": [{"label": g.get("suggested_label") or "", "members": " + ".join(g["members"]), "basis": g["basis"]} for g in sg]})
    sec.tables.append({"key": "settings", "title": c.t("t_set"), "columns": [col("name", c.t("c_name")), col("value", c.t("c_val")),
                                                                              col("source", c.t("c_source"))],
                       "rows": [{"name": k_, "value": a["thresholds"][k_], "source": a["thresholds_origin"][k_]} for k_ in a["thresholds"]]})
    rm.sections.append(sec)

    # ------------------------------------------------------------------ 9. custodians (admin only: personal data)
    if admin and holder_rows:
        sec = ReportSection(c.t("s_holder"), "holders")
        sec.tables.append({"key": "holders", "title": c.t("t_holder"), "columns": [
            col("holder", c.t("c_holder")), col("total", c.t("c_total"), "money"), col("share", c.t("c_share"), "pct"),
            col("lines", c.t("c_lines"), "int")], "rows": holder_rows, "pdf_rows": 20})
        rm.sections.append(sec)
    return rm


def _share(a: Decimal, b: Decimal):
    t = a + b
    return float(a / t * 100) if t else None


def _kpis(a: dict, c: Ctx) -> list[dict]:
    out = []
    for k in a["kpis"]:
        i = k["id"]
        if i == "total":
            out.append({"label": c.t("k_total"), "value": money(k["value"]), "sub": c.t("egp")})
        elif i == "avg_month":
            out.append({"label": c.t("k_avg"), "value": money(k["value"]), "sub": c.t("egp")})
        elif i == "peak_month":
            out.append({"label": c.t("k_peak"), "value": money(k["value"]), "sub": c.period(k["period"])})
        elif i == "low_month":
            out.append({"label": c.t("k_low"), "value": money(k["value"]), "sub": c.period(k["period"])})
        elif i == "last_vs_prev":
            out.append({"label": c.t("k_change"), "value": smoney(k["value"]), "sub": spct(k["pct"]),
                        "tone": "up" if k["value"] > 0 else "down"})
        elif i == "top_category":
            out.append({"label": c.t("k_topcat"), "value": k["name"], "sub": f"{money(k['value'])} · {pct(k['pct'])}"})
        elif i == "head_office_share":
            out.append({"label": c.t("k_ho"), "value": pct(k["pct"]), "sub": money(k["value"])})
        elif i == "top_branch":
            out.append({"label": c.t("k_topbr"), "value": k["name"], "sub": f"{money(k['value'])} · {pct(k['pct'])}"})
        elif i == "n_branches":
            out.append({"label": c.t("k_nbr"), "value": str(k["value"]), "sub": ""})
        elif i == "n_outliers":
            out.append({"label": c.t("k_out"), "value": str(k["value"]), "sub": ""})
        elif i == "n_facts":
            out.append({"label": c.t("k_lines"), "value": str(k["value"]), "sub": ""})
    return out


def _outlier_text(c: Ctx, o: dict) -> str:
    r = o["rule"]
    st = c.s.get("st_" + o["subject_type"], "")
    subj = o["subject"]
    if o["subject_type"] == "total":
        subj = c.t("total")
    elif o["subject_type"] == "scope":
        subj = c.t("ho") if subj == "head_office" else c.t("br")
    who = subj if o["subject_type"] == "total" else (f"{st} «{subj}»" if c.lang == "ar" else f"{st} “{subj}”")
    kw = dict(subject=subj, st=st, who=who, value=money(o["value"]) if o["value"] is not None else "", baseline=money(o["baseline"]) if o["baseline"] is not None else "",
              period=c.period(o["period"]) if o["period"] else "", abs=smoney(o["change_abs"]) if o["change_abs"] is not None else "",
              pct=spct(o["change_pct"]) if r == "mom_change" or r == "month_vs_average" else (pct(o["change_pct"]) if o["change_pct"] is not None else ""),
              ref=(o.get("refs") or [""])[0], refs=", ".join(o.get("refs", [])[:3]), count=o.get("count", ""),
              ind=c.t("ind") if o.get("indicative") else "")
    return c.t("r_" + r, **kw)
