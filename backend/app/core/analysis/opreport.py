"""Report fragments shared by the time-varying operating modules: file versions, the change log between versions, data-quality
observations and the settings used. A module's report adds its own analysis sections and calls these for the common ones."""
from app.core.reporting.base import ReportSection
from app.core.reporting.format import col

T = {
    "ar": {
        "s_versions": "النسخ والتغييرات", "s_quality": "جودة البيانات والإعدادات", "t_versions": "الملفات المرفوعة (من الأقدم إلى الأحدث؛ لا يُحذف شيء)",
        "t_changes": "التغييرات بين النسخ (القيمة السابقة محفوظة)", "t_issues": "ملاحظات على الملفات (معروضة كما هي دون تعديل)", "t_settings": "الإعدادات المستخدمة",
        "t_na": "غير متاح (لا تدعمه الملفات)", "c_file": "الملف", "c_layout": "نوع الملف", "c_uploaded": "تاريخ الرفع", "c_from": "من", "c_to": "إلى", "c_records": "السجلات",
        "c_added": "جديد عن السابق", "c_dropped": "غير موجود فيه", "c_changed": "قيم تغيّرت", "c_item": "البند", "c_period": "الفترة", "c_field": "الحقل", "c_old": "القيمة السابقة",
        "c_new": "القيمة الجديدة", "c_from_file": "من ملف", "c_to_file": "إلى ملف", "c_issue": "الملاحظة", "c_sev": "الأهمية", "c_n": "العدد", "c_examples": "أمثلة",
        "c_name": "الإعداد", "c_val": "القيمة", "c_origin": "المصدر", "sev_info": "للعلم", "sev_warning": "تنبيه", "sev_critical": "حرج",
        "i_versions": "الملف الأحدث رفعًا يحدد القيمة السارية لكل بند وفترة يذكرها؛ ما لا يذكره ملف جديد يبقى كما في الملف الأقدم. كل نسخة قديمة محفوظة وقابلة للمراجعة.",
        "x_one_version": "رُفع ملف واحد حتى الآن؛ ستظهر هنا الفروق عند رفع ملف محدّث.", "x_no_changes": "لا فروق في القيم بين النسخ المرفوعة.", "x_changes_cut": "عدد التغييرات {n}؛ يُعرض الأحدث فقط.",
        "default": "افتراضي", "custom": "معدَّل", "file_v": "نسخة", "layout_rent_register": "سجل عقود الإيجار", "layout_repairs_statement": "بيان إصلاحات السيارات", "layout_usage_report": "تقرير استخدام سيارة",
        "layout_maintenance_card": "كارت صيانة السيارات", "layout_overtime_monthly": "بيان الأجر الإضافي الشهري", "personal_hidden": "بيانات شخصية: أسماء الموظفين/الملّاك تظهر للمدير فقط؛ تُعرض الأكواد لغيره.",
    },
    "en": {
        "s_versions": "Versions and changes", "s_quality": "Data quality and settings", "t_versions": "Uploaded files (oldest to newest; nothing is deleted)",
        "t_changes": "Changes between versions (the previous value is kept)", "t_issues": "Observations on the files (shown as found, never fixed)", "t_settings": "Settings used",
        "t_na": "Not available (the files do not support it)", "c_file": "File", "c_layout": "File type", "c_uploaded": "Uploaded", "c_from": "From", "c_to": "To", "c_records": "Records",
        "c_added": "New vs previous", "c_dropped": "Not in this one", "c_changed": "Values changed", "c_item": "Item", "c_period": "Period", "c_field": "Field", "c_old": "Previous value",
        "c_new": "New value", "c_from_file": "From file", "c_to_file": "To file", "c_issue": "Observation", "c_sev": "Severity", "c_n": "Count", "c_examples": "Examples",
        "c_name": "Setting", "c_val": "Value", "c_origin": "Origin", "sev_info": "Info", "sev_warning": "Warning", "sev_critical": "Critical",
        "i_versions": "The most recently uploaded file decides the current value of each item and period it states; what a newer file does not state keeps its older value. Every older version is kept and can be reviewed.",
        "x_one_version": "Only one file has been uploaded so far; differences appear here when an updated file arrives.", "x_no_changes": "No value differences between the uploaded versions.",
        "x_changes_cut": "{n} changes; only the latest are listed.", "default": "default", "custom": "custom", "file_v": "version", "layout_rent_register": "Rent contract register",
        "layout_repairs_statement": "Vehicle repairs statement", "layout_usage_report": "Vehicle usage report", "layout_maintenance_card": "Vehicle maintenance card",
        "layout_overtime_monthly": "Monthly overtime statement", "personal_hidden": "Personal data: employee / landlord names are shown to admins only; others see codes.",
    },
}


class C:
    """Translator over a module's own table plus the shared one."""

    def __init__(self, lang: str, own: dict):
        self.lang = lang
        self.s = {**T[lang], **own[lang]}

    def t(self, key, **kw):
        return self.s[key].format(**kw) if kw else self.s[key]


def fmt_val(v) -> str:
    if isinstance(v, bool):
        return "✓" if v else "—"
    if isinstance(v, (int, float)):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1e12 else str(v)
    return "—" if v is None else str(v)


def versions_section(c: C, versions: list[dict], changes: list[dict], label_of, field_label, period_label, max_changes: int = 60) -> ReportSection:
    sec = ReportSection(c.t("s_versions"), "versions")
    sec.insights.append({"severity": "info", "text": c.t("i_versions")})
    names = {v["id"]: f"{c.t('file_v')} {i}" for i, v in enumerate(versions, 1)}
    sec.tables.append({"key": "versions", "title": c.t("t_versions"), "columns": [
        col("v", c.t("c_file")), col("layout", c.t("c_layout")), col("up", c.t("c_uploaded")), col("fr", c.t("c_from")), col("to", c.t("c_to")), col("n", c.t("c_records"), "int"),
        col("add", c.t("c_added"), "int"), col("drop", c.t("c_dropped"), "int"), col("chg", c.t("c_changed"), "int")],
        "rows": [{"v": f"{names[v['id']]} · {v['file']}", "layout": c.s.get("layout_" + v["layout"], v["layout"]), "up": v["uploaded_at"], "fr": v["from"] or "—", "to": v["to"] or "—", "n": v["records"],
                  "add": v["added"], "drop": v["dropped"], "chg": v["changed"]} for v in versions]})
    if len(versions) < 2:
        sec.insights.append({"severity": "info", "text": c.t("x_one_version")})
    elif not changes:
        sec.insights.append({"severity": "info", "text": c.t("x_no_changes")})
    if changes:
        shown = sorted(changes, key=lambda x: (x["to_dataset"], str(x["period"] or "")), reverse=True)[:max_changes]
        if len(changes) > len(shown):
            sec.insights.append({"severity": "info", "text": c.t("x_changes_cut", n=len(changes))})
        sec.tables.append({"key": "changes", "title": c.t("t_changes"), "columns": [
            col("item", c.t("c_item")), col("period", c.t("c_period")), col("field", c.t("c_field")), col("old", c.t("c_old")), col("new", c.t("c_new")), col("f", c.t("c_from_file")), col("t", c.t("c_to_file"))],
            "rows": [{"item": label_of(x), "period": period_label(x["period"]) if x["period"] else "—", "field": field_label(x["field"]), "old": fmt_val(x["old"]), "new": fmt_val(x["new"]),
                      "f": names.get(x["from_dataset"], str(x["from_dataset"])), "t": names.get(x["to_dataset"], str(x["to_dataset"]))} for x in shown], "pdf_rows": 40})
    return sec


def quality_section(c: C, issues: list[dict], th: dict, th_origin: dict, not_available: list[str], extra_tables: list[dict] | None = None, notes: list[str] | None = None) -> ReportSection:
    sec = ReportSection(c.t("s_quality"), "quality")
    for n in notes or []:
        sec.insights.append({"severity": "info", "text": n})
    if not_available:
        sec.insights.append({"severity": "info", "text": c.t("t_na") + ":"})
        sec.insights += [{"severity": "info", "text": x} for x in not_available]
    sec.tables += extra_tables or []
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [col("msg", c.t("c_issue")), col("sev", c.t("c_sev")), col("n", c.t("c_n"), "int"), col("ex", c.t("c_examples"))],
                       "rows": [{"msg": i["message"], "sev": c.s.get("sev_" + i["severity"], i["severity"]), "n": i["count"], "ex": " | ".join(i["examples"][:4])} for i in issues], "pdf_rows": 40})
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_val")), col("o", c.t("c_origin"))],
                       "rows": [{"n": k, "v": th[k], "o": c.t(th_origin.get(k, "default"))} for k in th]})
    return sec


def merged_issues(dataset_summaries: list[dict]) -> list[dict]:
    """Issues of every uploaded file, by code (the same observation in two versions is one row; counts are the latest file's)."""
    out: dict[str, dict] = {}
    for s in dataset_summaries:
        for i in s.get("issues", []):
            out[i["code"]] = i
    return sorted(out.values(), key=lambda i: ({"critical": 0, "warning": 1}.get(i["severity"], 2), i["code"]))
