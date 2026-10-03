"""ReportModel for the temporary-advance register. Holder names are personal data and appear only for admins."""
from datetime import datetime, timezone

from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "تحليل السلف المؤقتة", "s_summary": "الملخص التنفيذي", "s_monthly": "الصرف والتسوية شهريًا", "s_branches": "الفروع والجهات", "s_ageing": "الأعمار والمدد والاستثناءات",
        "s_quality": "جودة البيانات والإعدادات", "egp": "ج.م", "adv": "سلفة", "hq": "المركز الرئيسي", "grp": "مجموعة فروع", "no_branch": "بدون فرع", "filtered": "عرض مفلتر",
        "k_n": "عدد السلف", "k_issued": "إجمالي المصروف", "k_avg": "متوسط السلفة", "k_closed": "سلف مسوّاة / مغلقة", "k_open": "سلف مفتوحة", "k_open_amt": "مبلغ المفتوح", "k_open_pct": "نسبة المفتوح من المصروف",
        "k_lag": "وسيط مدة التسوية", "k_asof": "آخر تاريخ في السجل", "days": "يوم",
        "c_month": "الشهر", "c_issued_n": "سلف مصروفة", "c_issued": "المبلغ المصروف", "c_settled_n": "سلف سُوّيت (بتاريخ التسوية)", "c_settled": "المبلغ المسوّى", "c_open_n": "المفتوح آخر الشهر (عدد)",
        "c_open": "المفتوح آخر الشهر (مبلغ)", "c_d": "تغير المصروف", "c_dp": "التغير %", "c_note": "ملاحظة", "c_branch": "الفرع / الجهة", "c_kind": "النوع", "c_n": "عدد", "c_share": "النسبة %",
        "c_closed": "المغلق", "c_lag": "متوسط المدة (يوم)", "c_oldest": "أقدم مفتوح (يوم)", "c_band": "الفئة العمرية", "c_amount": "المبلغ", "c_key": "البيان", "c_val": "القيمة",
        "c_date": "التاريخ", "c_age": "العمر (يوم)", "c_purpose": "الغرض", "c_holder": "الحامل (بيانات شخصية)", "c_flag": "الاستثناء", "c_source": "المصدر", "c_issue": "الملاحظة", "c_sev": "الأهمية",
        "c_count": "العدد", "c_examples": "أمثلة", "c_stated": "المعلن في السجل", "c_computed": "المحسوب", "c_diff": "الفرق", "c_other": "الرقم الثاني المعلن (غير موضّح المعنى)", "c_bal": "المفتوح آخر الشهر (محسوب بالتواريخ)", "c_obd": "الفرق (الرقم الثاني − المحسوب)",
        "x_second": "الرقم الثاني المكتوب يدويًا في صفوف «اقفال الشهر» (معناه غير مذكور) يساوي المفتوح آخر الشهر المحسوب بالتواريخ في {m} من {n} شهور؛ للمقارنة فقط ولا يُعتمد.", "c_name": "الإعداد", "c_origin": "المصدر",
        "c_status": "الحالة",
        "t_months": "المؤشرات حسب الشهر", "t_branches": "السلف حسب الفرع / الجهة", "t_ageing": "أعمار السلف المفتوحة", "t_lag": "مدة التسوية", "t_exc": "ملخص الاستثناءات", "t_largest": "أكبر السلف",
        "t_open": "السلف المفتوحة الأقدم", "t_repeat": "فروع تكررت لها السلف", "t_controls": "ضبط إجماليات «اقفال الشهر» في السجل", "t_issues": "ملاحظات جودة البيانات", "t_settings": "الإعدادات المستخدمة",
        "ch_month": "المصروف والمسوّى شهريًا", "ch_branch": "أعلى الفروع صرفًا",
        "a1": "حتى {hi} يوم", "a2": "{lo}–{hi} يوم", "a3": "{lo}–{hi} يوم", "a4": "أكثر من {lo} يوم",
        "ex_large": "سلفة كبيرة مقارنة بالوسيط", "ex_long_settlement": "تسوية استغرقت أكثر من الحد", "ex_settled_before": "تسوية قبل تاريخ السلفة", "ex_closed_undated": "مغلقة بلا تاريخ تسوية مقروء",
        "ex_no_date": "سلفة بلا تاريخ", "ex_oldest_open": "مفتوحة أقدم من آخر فئة عمرية",
        "x_total": "صُرفت {n} سلفة بإجمالي {v} ج.م (متوسط {a} ج.م) حتى {d}؛ منها {c} مغلقة ({cv} ج.م) و{o} مفتوحة بمبلغ {ov} ج.م ({op} من المصروف).",
        "x_lag": "وسيط مدة التسوية {m} يومًا (أقصى {x})، وفي {l} سلفة أكثر من {t} يومًا.",
        "x_age": "من السلف المفتوحة {n} سلفة ({v} ج.م) أقدم من {d} يومًا.",
        "x_top": "أعلى جهة صرفًا «{b}» ({v} ج.م، {p}).", "x_month": "أعلى شهر صرفًا {m} ({v} ج.م، {n} سلفة).",
        "x_undated": "{n} سلفة مغلقة بلا تاريخ تسوية مقروء: لا تدخل في مدد التسوية ولا في الرصيد المفتوح بالتاريخ.",
        "x_control": "إجماليات «اقفال الشهر» في السجل تطابق المحسوب لكل الشهور ({n}).", "x_control_diff": "{d} من {n} إجماليات «اقفال الشهر» تختلف عن المحسوب (انظر الجودة).",
        "i_basis": "السجل لا يذكر حالة أو اعتمادًا أو رقم مستند؛ الحالة هنا مستنتجة من نص عمود «عهد تحت التسوية»: وجود تاريخ تسوية = مسوّاة، وغياب النص = مفتوحة حتى آخر تاريخ في السجل.",
        "i_asof": "الأعمار محسوبة حتى {d} (آخر تاريخ ورد في السجل)، وليس تاريخ اليوم.",
        "i_balance": "الرصيد المفتوح آخر كل شهر يعتمد على السلف ذات التواريخ الكاملة؛ استُبعد منه {n} سلفة (بلا تاريخ تسوية مقروء أو بلا تاريخ).",
        "i_group": "جهات مثل «فروع البحيرة» مجموعات فروع كما كُتبت في السجل ولا تُوزَّع على فروعها.",
        "i_filtered": "العرض مفلتر؛ ضبط «اقفال الشهر» لا يظهر مع الفلاتر.", "i_partial": "آخر شهر في السجل غير مكتمل.",
        "f_periods": "شهر السلفة", "f_branches": "الفرع / الجهة", "f_states": "الحالة", "s_open": "مفتوحة", "s_closed": "مغلقة",
        "sev_critical": "حرج", "sev_warning": "تنبيه", "sev_info": "للعلم", "ok": "مطابق", "bad": "فرق",
    },
    "en": {
        "title": "Temporary advances analysis", "s_summary": "Executive summary", "s_monthly": "Issued and settled by month", "s_branches": "Branches and units", "s_ageing": "Ageing, lag and exceptions",
        "s_quality": "Data quality and settings", "egp": "EGP", "adv": "advances", "hq": "Head Office", "grp": "Branch group", "no_branch": "No branch", "filtered": "Filtered view",
        "k_n": "Advances", "k_issued": "Total issued", "k_avg": "Average advance", "k_closed": "Settled / closed", "k_open": "Open advances", "k_open_amt": "Open amount", "k_open_pct": "Open share of issued",
        "k_lag": "Median settlement time", "k_asof": "Latest date in the register", "days": "days",
        "c_month": "Month", "c_issued_n": "Advances issued", "c_issued": "Amount issued", "c_settled_n": "Advances settled (by settlement date)", "c_settled": "Amount settled", "c_open_n": "Open at month end (count)",
        "c_open": "Open at month end (amount)", "c_d": "Change in issued", "c_dp": "Change %", "c_note": "Note", "c_branch": "Branch / unit", "c_kind": "Kind", "c_n": "Count", "c_share": "Share %",
        "c_closed": "Closed", "c_lag": "Avg time (days)", "c_oldest": "Oldest open (days)", "c_band": "Age band", "c_amount": "Amount", "c_key": "Item", "c_val": "Value",
        "c_date": "Date", "c_age": "Age (days)", "c_purpose": "Purpose", "c_holder": "Holder (personal data)", "c_flag": "Exception", "c_source": "Source", "c_issue": "Issue", "c_sev": "Severity",
        "c_count": "Count", "c_examples": "Examples", "c_stated": "Stated in the register", "c_computed": "Computed", "c_diff": "Difference", "c_other": "Second stated figure (meaning not documented)", "c_bal": "Open at month end (computed from the dates)", "c_obd": "Difference (second figure − computed)",
        "x_second": "The second hand-typed figure on the «month closing» rows (meaning not stated) equals the dated month-end open balance in {m} of {n} months; shown for comparison only, not relied on.", "c_name": "Setting", "c_origin": "Origin",
        "c_status": "Status",
        "t_months": "Indicators by month", "t_branches": "Advances by branch / unit", "t_ageing": "Age of open advances", "t_lag": "Settlement time", "t_exc": "Exception summary", "t_largest": "Largest advances",
        "t_open": "Oldest open advances", "t_repeat": "Branches with repeated advances", "t_controls": "Control of the register's «month closing» totals", "t_issues": "Data-quality notes", "t_settings": "Settings used",
        "ch_month": "Issued and settled by month", "ch_branch": "Top units by amount issued",
        "a1": "up to {hi} days", "a2": "{lo}–{hi} days", "a3": "{lo}–{hi} days", "a4": "over {lo} days",
        "ex_large": "Large vs the median advance", "ex_long_settlement": "Settlement took longer than the limit", "ex_settled_before": "Settled before the advance date", "ex_closed_undated": "Closed without a readable settlement date",
        "ex_no_date": "Advance without a date", "ex_oldest_open": "Open and older than the last age band",
        "x_total": "{n} advances were issued for {v} EGP (average {a} EGP) up to {d}; {c} are closed ({cv} EGP) and {o} are open for {ov} EGP ({op} of issued).",
        "x_lag": "Median settlement time {m} days (max {x}); {l} advances took longer than {t} days.",
        "x_age": "{n} open advances ({v} EGP) are older than {d} days.",
        "x_top": "Top unit by amount «{b}» ({v} EGP, {p}).", "x_month": "Highest month: {m} ({v} EGP, {n} advances).",
        "x_undated": "{n} advances are closed without a readable settlement date: they are outside settlement times and the dated open balance.",
        "x_control": "The register's «month closing» totals agree with the computed ones for all months ({n}).", "x_control_diff": "{d} of {n} «month closing» totals differ from the computed ones (see quality).",
        "i_basis": "The register states no status, approval or document number; the state here is read from the «settlement» column: a settlement date = settled, no text = open up to the latest date in the register.",
        "i_asof": "Ages are computed up to {d} (the latest date in the register), not today's date.",
        "i_balance": "The month-end open balance uses advances with complete dates; {n} advances (closed without a readable date, or undated) are excluded from it.",
        "i_group": "Units such as «Behira branches» are branch groups as written in the register and are not split across their branches.",
        "i_filtered": "Filtered view; the «month closing» control is not shown with filters.", "i_partial": "The latest month in the register is incomplete.",
        "f_periods": "Advance month", "f_branches": "Branch / unit", "f_states": "State", "s_open": "Open", "s_closed": "Closed",
        "sev_critical": "Critical", "sev_warning": "Warning", "sev_info": "Info", "ok": "Match", "bad": "Differs",
    },
}


class C:
    def __init__(self, lang):
        self.lang, self.s = lang, T[lang]

    def t(self, key, **kw):
        return self.s[key].format(**kw) if kw else self.s[key]

    def branch(self, label, kind):
        return self.t("hq") if kind == "head_office" else (label or self.t("no_branch"))


def build_report(ds, a: dict, all_rows: list[dict], lang: str, admin: bool, th: dict, origin: dict, filters: dict, issues: list[dict]) -> ReportModel:
    c = C(lang)
    t, months = a["totals"], a["months"]
    rm = ReportModel(title=c.t("title"), period_label=(f"{period_label(lang, months[0]['period'])} – {period_label(lang, months[-1]['period'])}" if months else ""), sections=[], lang=lang)
    rm.subtitle = f"{ds.file_name}" + (" · " + c.t("filtered") if a["filtered"] else "")
    ym = lambda d: d.strftime("%Y-%m") if d else None  # noqa: E731
    keys: dict[str, tuple] = {}
    for x in all_rows:
        keys.setdefault(x["branch_key"] or "none", (x["branch_label"], x["branch_kind"]))
    dims = [{"key": "periods", "param": "period", "label": c.t("f_periods"), "searchable": False,
             "items": [{"id": m, "label": period_label(lang, (int(m[:4]), int(m[5:])))} for m in sorted({ym(x["advance_on"]) for x in all_rows if x["advance_on"]})]},
            {"key": "branches", "param": "branch", "label": c.t("f_branches"), "searchable": True,
             "items": sorted(({"id": k, "label": c.branch(v[0], v[1])} for k, v in keys.items()), key=lambda i: i["label"])},
            {"key": "states", "param": "state", "label": c.t("f_states"), "searchable": False, "items": [{"id": "open", "label": c.t("s_open")}, {"id": "closed", "label": c.t("s_closed")}]}]
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": ds.file_name, "file_hash": ds.file_hash[:16],
               "filters": {"active": filters, "options": {}, "dimensions": dims}}
    as_of = a["as_of"]
    lag, ex = a["lag"], a["exceptions"]

    # ---------------------------------------------------------------- summary
    items = [{"metric": "total", "text": c.t("x_total", n=t["n"], v=money2(t["issued"]), a=money2(t["avg"]) if t["avg"] is not None else "—", d=as_of.isoformat() if as_of else "—", c=t["closed_n"],
                                              cv=money2(t["closed_amount"]), o=t["open_n"], ov=money2(t["open_amount"]), op=pct(t["open_pct"]))}]
    if lag["median"] is not None:
        items.append({"metric": "lag", "text": c.t("x_lag", m=f"{lag['median']:g}", x=lag["max"], l=lag["long"], t=th["long_settlement_days"])})
    old = ex["oldest_open"]
    if old:
        items.append({"metric": "age", "text": c.t("x_age", n=len(old), v=money2(sum((x["amount"] for x in old), 0)), d=th["ageing_days_3"])})
    if a["branches"]:
        tb = a["branches"][0]
        items.append({"metric": "top", "text": c.t("x_top", b=c.branch(tb["label"], tb["kind"]), v=money2(tb["issued"]), p=pct(tb["share"]))})
    if months:
        pk = max(months, key=lambda m: m["issued"])
        items.append({"metric": "month", "text": c.t("x_month", m=period_label(lang, pk["period"]), v=money2(pk["issued"]), n=pk["issued_n"])})
    if t["undated_closed_n"]:
        items.append({"metric": "undated", "text": c.t("x_undated", n=t["undated_closed_n"])})
    if not a["filtered"] and a["controls"]:
        bad = sum(1 for k in a["controls"] if k["stated"] is not None and k["stated"] != k["computed"])
        items.append({"metric": "control", "text": c.t("x_control", n=len(a["controls"])) if not bad else c.t("x_control_diff", d=bad, n=len(a["controls"]))})
    pairs = [k for k in a["controls"] if k.get("other_vs_balance") is not None]
    if pairs and not a["filtered"]:
        items.append({"metric": "second_figure", "text": c.t("x_second", m=sum(1 for k in pairs if k["other_vs_balance"] == 0), n=len(pairs))})
    if months and months[-1]["partial"]:
        items.append({"metric": "partial", "text": c.t("i_partial")})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = [{"label": c.t("k_n"), "value": f"{t['n']:,}", "sub": c.t("adv")}, {"label": c.t("k_issued"), "value": money2(t["issued"]), "sub": c.t("egp")},
                {"label": c.t("k_avg"), "value": money2(t["avg"]) if t["avg"] is not None else "—", "sub": c.t("egp")}, {"label": c.t("k_closed"), "value": str(t["closed_n"]), "sub": money2(t["closed_amount"]) + " " + c.t("egp")},
                {"label": c.t("k_open"), "value": str(t["open_n"]), "sub": pct(t["open_pct"]), "tone": "up" if t["open_n"] else ""}, {"label": c.t("k_open_amt"), "value": money2(t["open_amount"]), "sub": c.t("egp")},
                {"label": c.t("k_lag"), "value": f"{lag['median']:g}" if lag["median"] is not None else "—", "sub": c.t("days")}, {"label": c.t("k_asof"), "value": as_of.isoformat() if as_of else "—", "sub": ""}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights += [{"severity": "info", "text": c.t("i_basis")}, {"severity": "info", "text": c.t("i_asof", d=as_of.isoformat() if as_of else "—")}]
    rm.sections.append(sec)

    # ---------------------------------------------------------------- months
    sec = ReportSection(c.t("s_monthly"), "monthly")
    if months:
        x = [period_label(lang, m["period"], True) for m in months]
        sec.charts.append({"type": "bar", "title": c.t("ch_month"), "x": x, "series": [{"name": c.t("c_issued"), "values": [float(m["issued"]) for m in months]},
                                                                                   {"name": c.t("c_settled"), "values": [float(m["settled"]) for m in months]}]})
        sec.tables.append({"key": "months", "title": c.t("t_months"), "columns": [
            col("period", c.t("c_month")), col("in", c.t("c_issued_n"), "int"), col("ia", c.t("c_issued"), "money"), col("sn", c.t("c_settled_n"), "int"), col("sa", c.t("c_settled"), "money"),
            col("on", c.t("c_open_n"), "int"), col("oa", c.t("c_open"), "money"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dp"), "spct"), col("note", c.t("c_note"))],
            "rows": [{"period": period_label(lang, m["period"]), "in": m["issued_n"], "ia": m["issued"], "sn": m["settled_n"], "sa": m["settled"], "on": m["open_n"], "oa": m["open"],
                      "d": m.get("d_issued"), "dp": m.get("d_issued_pct"), "note": c.t("i_partial") if m["partial"] else ""} for m in months]})
        if a["excluded_from_balance"]:
            sec.insights.append({"severity": "info", "text": c.t("i_balance", n=a["excluded_from_balance"])})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- branches
    sec = ReportSection(c.t("s_branches"), "branches")
    top = a["branches"][: int(th["top_n"])]
    if top:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_branch"), "x": [c.branch(b["label"], b["kind"]) for b in top], "series": [{"name": c.t("c_issued"), "values": [float(b["issued"]) for b in top]}]})
    sec.tables.append({"key": "branches", "title": c.t("t_branches"), "columns": [
        col("b", c.t("c_branch")), col("kind", c.t("c_kind")), col("n", c.t("c_n"), "int"), col("issued", c.t("c_issued"), "money"), col("share", c.t("c_share"), "pct"),
        col("cn", c.t("c_closed"), "int"), col("on", c.t("k_open"), "int"), col("oa", c.t("k_open_amt"), "money"), col("lag", c.t("c_lag"), "num"), col("old", c.t("c_oldest"), "int")],
        "rows": [{"b": c.branch(b["label"], b["kind"]), "kind": c.t("hq") if b["kind"] == "head_office" else (c.t("grp") if b["kind"] == "group" else ""), "n": b["n"], "issued": b["issued"], "share": b["share"],
                  "cn": b["closed_n"], "on": b["open_n"], "oa": b["open"], "lag": b["avg_lag"], "old": b["oldest"]} for b in a["branches"]], "pdf_rows": 50})
    if any(b["kind"] == "group" for b in a["branches"]):
        sec.insights.append({"severity": "info", "text": c.t("i_group")})
    if a["repeating"]:
        sec.tables.append({"key": "repeating", "title": c.t("t_repeat"), "columns": [col("b", c.t("c_branch")), col("n", c.t("c_n"), "int"), col("issued", c.t("c_issued"), "money")],
                           "rows": [{"b": c.branch(b["label"], b["kind"]), "n": b["n"], "issued": b["issued"]} for b in a["repeating"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- ageing / lag / exceptions
    sec = ReportSection(c.t("s_ageing"), "ageing")

    def band(w):
        return c.t(w["key"], lo=w["lo"], hi=w["hi"])
    sec.tables.append({"key": "ageing", "title": c.t("t_ageing"), "columns": [col("band", c.t("c_band")), col("n", c.t("c_n"), "int"), col("amount", c.t("c_amount"), "money")],
                       "rows": [{"band": band(w), "n": w["n"], "amount": w["amount"]} for w in a["ageing"]]})
    sec.tables.append({"key": "lag", "title": c.t("t_lag"), "columns": [col("k", c.t("c_key")), col("v", c.t("c_val"), "num")], "rows": [
        {"k": "n", "v": lag["n"]}, {"k": "median", "v": lag["median"]}, {"k": "mean", "v": lag["mean"]}, {"k": "p90", "v": lag["p90"]}, {"k": "max", "v": lag["max"]}]})
    sec.tables.append({"key": "exc_summary", "title": c.t("t_exc"), "columns": [col("f", c.t("c_flag")), col("n", c.t("c_n"), "int"), col("amount", c.t("c_amount"), "money")],
                       "rows": [{"f": c.t("ex_" + k), "n": len(v), "amount": sum((x["amount"] for x in v), 0)} for k, v in ex.items() if v]})
    ocols = [col("b", c.t("c_branch")), col("d", c.t("c_date")), col("amount", c.t("c_amount"), "money"), col("age", c.t("c_age"), "int"), col("p", c.t("c_purpose"))] + ([col("h", c.t("c_holder"))] if admin else [])

    def orow(x):
        r = {"b": c.branch(x["branch_label"], x["branch_kind"]), "d": x["advance_on"].isoformat() if x["advance_on"] else "", "amount": x["amount"],
             "age": (as_of - x["advance_on"]).days if as_of and x["advance_on"] else None, "p": (x["purpose"] or "")[:70]}
        if admin:
            r["h"] = x["holder"]
        return r
    if ex["oldest_open"]:
        sec.tables.append({"key": "open_old", "title": c.t("t_open"), "columns": ocols, "rows": [orow(x) for x in ex["oldest_open"][:30]], "pdf_rows": 30})
    sec.tables.append({"key": "largest", "title": c.t("t_largest"), "columns": ocols, "rows": [orow(x) for x in a["largest"]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- quality
    sec = ReportSection(c.t("s_quality"), "quality")
    if a["filtered"]:
        sec.insights.append({"severity": "info", "text": c.t("i_filtered")})
    else:
        sec.tables.append({"key": "controls", "title": c.t("t_controls"), "columns": [col("l", c.t("c_key")), col("s", c.t("c_stated"), "money"), col("c", c.t("c_computed"), "money"),
                                                                                       col("d", c.t("c_diff"), "smoney"), col("st", c.t("c_status")),
                                                                                       col("o", c.t("c_other"), "money"), col("b", c.t("c_bal"), "money"), col("od", c.t("c_obd"), "smoney")],
                           "rows": [{"l": k["label"], "s": k["stated"], "c": k["computed"], "d": (k["computed"] - k["stated"]) if k["stated"] is not None else None,
                                     "st": c.t("ok") if k["stated"] is not None and k["stated"] == k["computed"] else c.t("bad"), "o": k["other_stated"], "b": k["open_balance"],
                                     "od": k["other_vs_balance"]} for k in a["controls"]]})
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [col("m", c.t("c_issue")), col("sev", c.t("c_sev")), col("n", c.t("c_count"), "int"), col("ex", c.t("c_examples"))],
                       "rows": [{"m": i["message"], "sev": c.t("sev_" + i["severity"]), "n": i["count"], "ex": " | ".join(i["examples"][:3]) if admin else ("" if any(w in i["code"] for w in ("duplicate",)) else " | ".join(i["examples"][:3]))} for i in issues], "pdf_rows": 25})
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_val")), col("o", c.t("c_origin"))], "rows": [{"n": k, "v": th[k], "o": origin[k]} for k in th]})
    rm.sections.append(sec)
    return rm


_ = (smoney, spct)
