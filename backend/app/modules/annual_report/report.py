"""ReportModel for the annual administrative operating cost report. Sentences come from computed numbers only; what the data does not support is
stated as «not available», and what is left out of the official figures is listed with its reason."""
from datetime import datetime, timezone

from app.core.analysis.opreport import C as BaseC, merged_issues
from app.core.reporting.base import ReportModel, ReportSection
from app.core.reporting.format import col, money, money2, pct, period_label, smoney, spct

T = {
    "ar": {
        "title": "التقرير السنوي لتكلفة التشغيل الإداري", "s_summary": "الملخص التنفيذي", "s_cost": "تكلفة التشغيل الإداري (إيجار + سيارات) واتجاهها الشهري", "s_rent": "الإيجارات", "s_fleet": "السيارات: الصيانة والوقود",
        "s_vehicles": "تحليل تكلفة كل سيارة", "s_ot": "الأجر الإضافي (ساعات)", "s_compare": "المقارنات الشهرية والسنوية", "s_drivers": "أكبر محركات التكلفة", "s_moves": "أهم الزيادات والانخفاضات",
        "s_signals": "إشارات للمراجعة وفرص خفض التكلفة", "s_kpis": "أهم المؤشرات لكل وحدة", "s_quality": "جودة البيانات والاستثناءات وما لا يدخل في الأرقام الرسمية", "s_versions": "سجل النسخ والتغييرات",
        "egp": "ج.م", "hours": "ساعة", "unalloc": "Unallocated / يحتاج مراجعة", "hq": "المركز الرئيسي", "na": "غير متاح", "yr": "سنة",
        "k_total": "تكلفة التشغيل الإداري", "k_rent": "الإيجارات", "k_fleet": "السيارات", "k_avg": "متوسط الشهر", "k_share": "حصة الإيجار", "k_ot": "ساعات الأجر الإضافي", "k_months": "أشهر المقارنة المشتركة",
        "c_period": "الشهر", "c_rent": "الإيجار", "c_fleet": "السيارات", "c_total": "الإجمالي", "c_d": "التغير", "c_dpct": "التغير %", "c_ot": "ساعات إضافي", "c_note": "ملاحظة", "c_gov": "المحافظة", "c_amount": "المبلغ",
        "c_share": "النسبة من الإجمالي %", "c_share_c": "النسبة من المكوّن %", "c_name": "البند", "c_maint": "الصيانة", "c_fuel": "الوقود", "c_plate": "السيارة", "c_type": "النوع", "c_months": "أشهر", "c_cpk": "تكلفة/كم", "c_km": "كم",
        "c_day": "نهاري", "c_night": "ليلي", "c_weighted": "المكافئة", "c_active": "موظفون لهم إضافي", "c_code": "الكود", "c_emp": "الموظف", "c_hours": "الساعات", "c_first": "أول شهر", "c_last": "آخر شهر",
        "c_old": "السابق", "c_new": "الحالي", "c_pct": "%", "c_this": "هذه السنة", "c_prev": "السنة السابقة", "c_module": "الوحدة", "c_status": "الحالة", "c_effect": "الأثر على الأرقام", "c_detail": "تفاصيل", "c_kpi": "المؤشر",
        "c_value": "القيمة", "c_basis": "الأساس", "c_end": "نهاية العقد", "c_cur": "آخر قيمة", "c_file": "الملف", "c_layout": "النوع", "c_up": "تاريخ الرفع", "c_from": "من", "c_to": "إلى", "c_records": "السجلات",
        "c_added": "جديد", "c_dropped": "غير موجود", "c_changed": "تغيّرت", "c_item": "البند", "c_field": "الحقل", "c_issue": "الملاحظة", "c_sev": "الأهمية", "c_n": "العدد", "c_ex": "أمثلة", "c_set": "الإعداد", "c_origin": "المصدر",
        "c_claim": "المطالبة", "c_orig": "أصل المبلغ", "c_company": "تحمل الشركة", "c_factor": "المضاعف", "c_median": "وسيط السيارة",
        "t_cost": "الأشهر: الإيجار والسيارات والإجمالي والأجر الإضافي", "t_rent_m": "الإيجار المسجّل شهريًا", "t_rent_g": "الإيجار حسب المحافظة (الأشهر المكتملة)", "t_fleet_m": "تكلفة السيارات شهريًا",
        "t_cats": "بنود تكلفة السيارات", "t_veh": "تكلفة كل سيارة", "t_ot_m": "الساعات الشهرية", "t_ot_e": "الموظفون (ساعات السنة)", "t_mom": "التغير الشهري للتكلفة المجمعة", "t_yoy_r": "الإيجار: نفس الشهر في السنة السابقة",
        "t_yoy_f": "السيارات: نفس الشهر في السنة السابقة", "t_yoy_o": "الأجر الإضافي: نفس الشهر في السنة السابقة", "t_d_rg": "محركات الإيجار: المحافظات", "t_d_rc": "محركات الإيجار: أعلى العقود", "t_d_fc": "محركات السيارات: بنود التكلفة",
        "t_d_fv": "محركات السيارات: أعلى السيارات", "t_split": "تركيب التكلفة", "t_m_rr": "الإيجار: أكبر الزيادات (قيمة العقد من أول شهر مكتمل إلى آخر شهر مكتمل)", "t_m_rf": "الإيجار: أكبر الانخفاضات", "t_m_fr": "السيارات: أكبر الزيادات عن الشهر السابق",
        "t_m_ff": "السيارات: أكبر الانخفاضات عن الشهر السابق", "t_m_or": "الأجر الإضافي: أكبر الزيادات عن الشهر السابق (ساعات)", "t_m_of": "الأجر الإضافي: أكبر الانخفاضات عن الشهر السابق (ساعات)",
        "t_sig_exp": "إيجار: عقود تنتهي قريبًا (موعد قرار تجديد أو تفاوض)", "t_sig_inc": "إيجار: أعلى نسب الزيادة العادية في السنة", "t_sig_cpk": "سيارات: أعلى تكلفة للكيلومتر", "t_sig_out": "سيارات: أشهر أعلى كثيرًا من وسيط السيارة",
        "t_sig_claims": "سيارات: مطالبات تأمين تحمّلت الشركة جزءًا منها", "t_sig_ot": "أجر إضافي: أشهر موظفين أعلى كثيرًا من متوسطهم", "t_kpi": "المؤشرات", "t_excl": "ما لا يدخل في الأرقام الرسمية أو يحتاج مراجعة", "t_issues": "ملاحظات على الملفات حسب الوحدة",
        "t_settings": "الإعدادات المستخدمة", "t_versions": "الملفات المرفوعة (من الأقدم إلى الأحدث؛ لا يُحذف شيء)", "t_changes": "التغييرات بين النسخ (القيمة السابقة محفوظة)",
        "ch_cost": "تكلفة التشغيل الشهرية: إيجار وسيارات", "ch_ot": "ساعات الأجر الإضافي شهريًا", "ch_drv": "أكبر محركات التكلفة", "ch_gov": "الإيجار حسب المحافظة",
        "m_rent": "الإيجارات", "m_fleet": "السيارات", "m_ot": "الأجر الإضافي", "st_ok": "مكتمل", "st_partial": "جزئي", "st_missing": "غير متاح", "large": "تغير كبير",
        "x_cost": "تكلفة التشغيل الإداري (إيجار + سيارات) خلال {m}: {v} ج.م (إيجار {r} ج.م = {rp}، سيارات {f} ج.م)، بمتوسط {a} ج.م للشهر.",
        "x_scope": "الإجمالي المجمّع يُحسب للأشهر التي اكتمل فيها الإيجار والسيارات معًا فقط ({n} شهرًا)؛ غيرها لا يدخل فيه.", "x_nocommon": "لا يوجد شهر اكتمل فيه الإيجار والسيارات معًا في {y}؛ فلا يُحسب إجمالي تشغيل مجمّع، وتُعرض المكوّنات منفصلة.",
        "x_mom": "آخر تغير شهري: {p}: {d} ج.م ({pc}).", "x_peak": "أعلى شهر {pm} ({pv} ج.م) وأقلها {lm} ({lv} ج.م).", "x_rent": "الإيجارات {y}: {v} ج.م عن {n} شهرًا مكتملًا، منها المركز الرئيسي {h} ج.م.",
        "x_fleet": "السيارات {y}: {v} ج.م مذكورة (صيانة {m} ج.م، وقود {f} ج.م) لـ {n} سيارة.", "x_ot": "الأجر الإضافي {y}: {h} ساعة ({d} نهاري، {n} ليلي) في {k} شهرًا، بدون مبالغ في الملف، لذلك لا يُضاف إلى التكلفة المالية.",
        "x_driver": "أكبر محرك تكلفة: {n} ({v} ج.م، {s} من الإجمالي المجمّع).", "x_excl": "{n} بندًا لا يدخل في الأرقام الرسمية أو يحتاج مراجعة؛ مفصَّل في قسم الجودة.", "x_noforec": "الأرقام تاريخية كما سُجلت؛ لا توقعات.",
        "x_na_mod": "{m}: لا توجد بيانات لهذه السنة.",
        "i_basis": "تكلفة التشغيل الإداري بالمال = الإيجار المسجّل + تكلفة السيارات المذكورة (صيانة + وقود) للأشهر المكتملة في الوحدتين. الأجر الإضافي بالساعات فقط لعدم وجود قيمة ساعة أو مبالغ، ولا يُحوَّل إلى مال.",
        "i_same": "الأرقام هي نفسها التي تعرضها لوحات الوحدات (نفس البيانات الفعّالة ونفس المحرك)؛ الشهر الجزئي أو غير المتاح لا يدخل في الأرقام الرسمية للوحدة ويُدرج في قسم الاستثناءات.",
        "i_signals": "إشارات للمراجعة مستخرجة من الأرقام وليست توصيات ولا تقديرًا لوفورات؛ القرار للإدارة بعد فحص السبب.", "i_personal": "أسماء الموظفين والملّاك والسائقين بيانات شخصية: تظهر للمدير فقط.",
        "i_nomoney_ot": "لا يوجد في بيان الأجر الإضافي مبالغ ولا قيمة ساعة: لذلك لا تُحسب تكلفته ولا تدخل في إجمالي التشغيل.",
        "i_yoy_na": "المقارنة بالسنة السابقة: لا توجد بيانات لنفس الأشهر في السنة السابقة", "i_no_data": "لا توجد بيانات",
        "sig_exp_note": "عقد ينتهي خلال {w} أشهر من آخر شهر مكتمل؛ {n} عقدًا خلال {x} شهرًا.", "sig_cpk_note": "تكلفة الكيلومتر تُحسب على الأشهر التي لها مسافة فقط.",
        "e_rent_partial": "أشهر إيجار ببيانات جزئية (لعدد قليل من العقود)", "e_rent_missing": "أشهر إيجار بلا بيانات في الملف", "e_rent_exc_excluded": "عقد مستبعد لتعارض نسخه", "e_rent_exc_resolved": "عقد حُسم تعارض نسخه بدليل",
        "e_fleet_partial": "شهر سيارات غير مكتمل غالبًا", "e_fleet_cand": "كتابات لوحة قد تخص سيارة واحدة ولم تُربط", "e_ot_excluded": "ورقة أجر إضافي مستبعدة", "e_ot_missing": "شهر أجر إضافي بلا كشف",
        "st_excluded": "مستبعد", "st_not_comparable": "خارج الأرقام الرسمية", "st_resolved": "حُسم (يُذكر للشفافية)", "st_review": "يحتاج مراجعة",
        "ef_rent_partial": "لا يدخل في إجمالي الإيجار ولا في المقارنات", "ef_rent_missing": "لا يُقدَّر ولا يُحتسب صفرًا", "ef_rent_excluded": "لا يدخل في أي رقم", "ef_rent_resolved": "يدخل بقيمة السجل المعتمد (انظر تقرير الإيجارات)",
        "ef_fleet_partial": "تكلفته المذكورة مدرجة في إجمالي السيارات، لكنه لا يدخل في الإجمالي المجمّع ولا المقارنات", "ef_fleet_cand": "تبقى سيارتين منفصلتين حتى يُعتمد مرادف في الإعدادات",
        "ef_ot_excluded": "لا يدخل في أي رقم؛ الشهر يبقى غير متاح حتى يصل كشفه الصحيح", "ef_ot_missing": "لا يُقدَّر ولا يُحتسب صفرًا",
        "c_sheet": "الورقة", "ctl_vehicles": "إجماليات مذكورة لا تطابق أجزاءها", "ef_ctl": "الرقم المعتمد هو مجموع الصفوف؛ الفرق معروض في تقرير السيارات",
        "fld_rent": "الإيجار", "fld_governorate": "المحافظة", "fld_start": "بداية العقد", "fld_end": "نهاية العقد", "fld_advance": "المقدم", "fld_deposit": "التأمين", "fld_contract_rent": "القيمة بالعقد", "fld_no_payment": "بلا سداد",
        "fld_maint_total": "إجمالي الصيانة", "fld_fuel_cost": "تكلفة الوقود", "fld_grand_total": "الإجمالي العام", "fld_km": "المسافة", "fld_day_hours": "ساعات نهاري", "fld_night_hours": "ساعات ليلي", "fld_weighted_total": "إجمالي مكافئ",
        "fld_meals": "وجبات", "fld_fuel_qty": "كمية الوقود", "fld_type": "النوع", "fld_note": "ملاحظة", "fld_odometer": "العداد", "fld_day_weighted": "نهاري مكافئ", "fld_night_weighted": "ليلي مكافئ",
        "sev_info": "للعلم", "sev_warning": "تنبيه", "sev_critical": "حرج", "default": "افتراضي", "custom": "معدَّل",
        "kp_rent_total": "إجمالي إيجار الأشهر المكتملة", "kp_rent_n": "عقود لها قيمة في آخر شهر", "kp_rent_avg": "متوسط الإيجار للعقد", "kp_rent_inc": "متوسط الزيادة العادية", "kp_rent_exp": "عقود تنتهي قريبًا", "kp_rent_adv": "المقدم المذكور (إجمالي)", "kp_rent_dep": "التأمين المذكور (إجمالي)",
        "kp_f_total": "إجمالي تكلفة السيارات المذكورة", "kp_f_maint": "الصيانة", "kp_f_fuel": "الوقود", "kp_f_cpk": "تكلفة الكيلومتر (أشهر لها مسافة)", "kp_f_veh": "سيارات لها تكلفة", "kp_f_claims": "مطالبات التأمين (أصل المبلغ)", "kp_f_due": "بنود صيانة مستحقة/قريبة",
        "kp_o_hours": "إجمالي الساعات", "kp_o_wtd": "الساعات المكافئة", "kp_o_night": "نسبة الليلي", "kp_o_conc": "حصة أعلى {n} موظفين", "kp_o_meals": "الوجبات", "kp_o_missions": "المأموريات", "kp_o_emp": "موظفون لهم إضافي",
    },
    "en": {
        "title": "Annual administrative operating cost report", "s_summary": "Executive summary", "s_cost": "Administrative operating cost (rent + fleet) and its monthly trend", "s_rent": "Rent", "s_fleet": "Fleet: maintenance and fuel",
        "s_vehicles": "Cost analysis per vehicle", "s_ot": "Overtime (hours)", "s_compare": "Monthly and annual comparisons", "s_drivers": "Top cost drivers", "s_moves": "Biggest increases and decreases",
        "s_signals": "Signals for review and cost-saving opportunities", "s_kpis": "Key indicators per module", "s_quality": "Data quality, exceptions and what is not in the official figures", "s_versions": "Version history and changes",
        "egp": "EGP", "hours": "h", "unalloc": "Unallocated / needs review", "hq": "Head Office", "na": "n/a", "yr": "year",
        "k_total": "Administrative operating cost", "k_rent": "Rent", "k_fleet": "Fleet", "k_avg": "Monthly average", "k_share": "Rent share", "k_ot": "Overtime hours", "k_months": "Months compared jointly",
        "c_period": "Month", "c_rent": "Rent", "c_fleet": "Fleet", "c_total": "Total", "c_d": "Change", "c_dpct": "Change %", "c_ot": "Overtime h", "c_note": "Note", "c_gov": "Governorate", "c_amount": "Amount",
        "c_share": "Share of total %", "c_share_c": "Share of component %", "c_name": "Item", "c_maint": "Maintenance", "c_fuel": "Fuel", "c_plate": "Vehicle", "c_type": "Type", "c_months": "Months", "c_cpk": "Cost/km", "c_km": "km",
        "c_day": "Day", "c_night": "Night", "c_weighted": "Weighted", "c_active": "Employees with overtime", "c_code": "Code", "c_emp": "Employee", "c_hours": "Hours", "c_first": "First month", "c_last": "Last month",
        "c_old": "Previous", "c_new": "Current", "c_pct": "%", "c_this": "This year", "c_prev": "Previous year", "c_module": "Module", "c_status": "Status", "c_effect": "Effect on the figures", "c_detail": "Details", "c_kpi": "Indicator",
        "c_value": "Value", "c_basis": "Basis", "c_end": "End date", "c_cur": "Latest value", "c_file": "File", "c_layout": "Type", "c_up": "Uploaded", "c_from": "From", "c_to": "To", "c_records": "Records",
        "c_added": "New", "c_dropped": "Not in it", "c_changed": "Changed", "c_item": "Item", "c_field": "Field", "c_issue": "Observation", "c_sev": "Severity", "c_n": "Count", "c_ex": "Examples", "c_set": "Setting", "c_origin": "Origin",
        "c_claim": "Claim", "c_orig": "Original amount", "c_company": "Company share", "c_factor": "Multiple", "c_median": "Vehicle median",
        "t_cost": "Months: rent, fleet, total and overtime", "t_rent_m": "Rent recorded by month", "t_rent_g": "Rent by governorate (complete months)", "t_fleet_m": "Fleet cost by month",
        "t_cats": "Fleet cost items", "t_veh": "Cost of each vehicle", "t_ot_m": "Monthly hours", "t_ot_e": "Employees (hours of the year)", "t_mom": "Month-on-month change of the combined cost", "t_yoy_r": "Rent: same month last year",
        "t_yoy_f": "Fleet: same month last year", "t_yoy_o": "Overtime: same month last year", "t_d_rg": "Rent drivers: governorates", "t_d_rc": "Rent drivers: largest contracts", "t_d_fc": "Fleet drivers: cost items",
        "t_d_fv": "Fleet drivers: largest vehicles", "t_split": "Cost composition", "t_m_rr": "Rent: biggest increases (contract rent from the first to the last complete month)", "t_m_rf": "Rent: biggest decreases", "t_m_fr": "Fleet: biggest increases vs the previous month",
        "t_m_ff": "Fleet: biggest decreases vs the previous month", "t_m_or": "Overtime: biggest increases vs the previous month (hours)", "t_m_of": "Overtime: biggest decreases vs the previous month (hours)",
        "t_sig_exp": "Rent: contracts ending soon (renewal / negotiation decision point)", "t_sig_inc": "Rent: highest regular increase rates in the year", "t_sig_cpk": "Fleet: highest cost per km", "t_sig_out": "Fleet: months far above the vehicle's median",
        "t_sig_claims": "Fleet: insurance claims the company partly bore", "t_sig_ot": "Overtime: employee-months far above their own average", "t_kpi": "Indicators", "t_excl": "What is not in the official figures or needs review", "t_issues": "Observations on the files by module",
        "t_settings": "Settings used", "t_versions": "Uploaded files (oldest to newest; nothing is deleted)", "t_changes": "Changes between versions (the previous value is kept)",
        "ch_cost": "Monthly operating cost: rent and fleet", "ch_ot": "Overtime hours by month", "ch_drv": "Top cost drivers", "ch_gov": "Rent by governorate",
        "m_rent": "Rent", "m_fleet": "Fleet", "m_ot": "Overtime", "st_ok": "Complete", "st_partial": "Partial", "st_missing": "n/a", "large": "Large change",
        "x_cost": "Administrative operating cost (rent + fleet) over {m}: {v} EGP (rent {r} EGP = {rp}, fleet {f} EGP), averaging {a} EGP a month.",
        "x_scope": "The combined total covers only months in which both rent and fleet are complete ({n} months); other months are not in it.", "x_nocommon": "No month of {y} is complete in both rent and fleet, so no combined operating cost is computed; the components are shown apart.",
        "x_mom": "Latest monthly change: {p}: {d} EGP ({pc}).", "x_peak": "Highest month {pm} ({pv} EGP) and lowest {lm} ({lv} EGP).", "x_rent": "Rent {y}: {v} EGP over {n} complete months, of which Head Office {h} EGP.",
        "x_fleet": "Fleet {y}: {v} EGP stated (maintenance {m} EGP, fuel {f} EGP) for {n} vehicles.", "x_ot": "Overtime {y}: {h} h ({d} day, {n} night) over {k} months; the file has no amounts, so it is not added to the money cost.",
        "x_driver": "Largest cost driver: {n} ({v} EGP, {s} of the combined total).", "x_excl": "{n} items are outside the official figures or need review; detailed in the quality section.", "x_noforec": "Figures are historical as recorded; no forecasts.",
        "x_na_mod": "{m}: no data for this year.",
        "i_basis": "Administrative operating cost in money = recorded rent + stated fleet cost (maintenance + fuel) for the months complete in both modules. Overtime is in hours only (no hourly value or amounts) and is not converted to money.",
        "i_same": "The figures are the same ones the module dashboards show (same effective data, same engine); a partial or unavailable month is not an official figure of its module and is listed in the exceptions.",
        "i_signals": "Signals for review drawn from the figures; they are not recommendations or savings estimates; the decision is management's after checking the cause.", "i_personal": "Employee, landlord and driver names are personal data: shown to admins only.",
        "i_nomoney_ot": "The overtime statement has no amounts or hourly value: its cost is not computed and it is not in the operating total.",
        "i_yoy_na": "Comparison with the previous year: there is no data for the same months in the previous year", "i_no_data": "No data",
        "sig_exp_note": "A contract ending within {w} months of the last complete month; {n} contracts within {x} months.", "sig_cpk_note": "Cost per km uses only months that have a distance.",
        "e_rent_partial": "Rent months with partial data (a few contracts only)", "e_rent_missing": "Rent months with no data in the file", "e_rent_exc_excluded": "Contract excluded because its copies conflict", "e_rent_exc_resolved": "Contract whose conflicting copies were settled by evidence",
        "e_fleet_partial": "Fleet month probably incomplete", "e_fleet_cand": "Plate spellings that may be one vehicle, not linked", "e_ot_excluded": "Overtime sheet excluded", "e_ot_missing": "Overtime month with no statement",
        "st_excluded": "Excluded", "st_not_comparable": "Outside the official figures", "st_resolved": "Settled (listed for transparency)", "st_review": "Needs review",
        "ef_rent_partial": "Not in the rent total or the comparisons", "ef_rent_missing": "Not estimated and not counted as zero", "ef_rent_excluded": "Not in any figure", "ef_rent_resolved": "Counted at the value of the record used (see the rent report)",
        "ef_fleet_partial": "Its stated cost is in the fleet total, but not in the combined total or the comparisons", "ef_fleet_cand": "Stay two vehicles until an alias is approved in the settings",
        "ef_ot_excluded": "In no figure; the month stays unavailable until its correct statement arrives", "ef_ot_missing": "Not estimated and not counted as zero",
        "c_sheet": "Sheet", "ctl_vehicles": "Stated totals that do not match their parts", "ef_ctl": "The figure used is the sum of the rows; the difference is shown in the fleet report",
        "fld_rent": "Rent", "fld_governorate": "Governorate", "fld_start": "Start", "fld_end": "End", "fld_advance": "Advance", "fld_deposit": "Deposit", "fld_contract_rent": "Contract rent", "fld_no_payment": "No payment",
        "fld_maint_total": "Maintenance total", "fld_fuel_cost": "Fuel cost", "fld_grand_total": "Grand total", "fld_km": "Distance", "fld_day_hours": "Day hours", "fld_night_hours": "Night hours", "fld_weighted_total": "Weighted total",
        "fld_meals": "Meals", "fld_fuel_qty": "Fuel quantity", "fld_type": "Type", "fld_note": "Note", "fld_odometer": "Odometer", "fld_day_weighted": "Day weighted", "fld_night_weighted": "Night weighted",
        "sev_info": "Info", "sev_warning": "Warning", "sev_critical": "Critical", "default": "default", "custom": "custom",
        "kp_rent_total": "Rent of the complete months", "kp_rent_n": "Contracts with a value in the last month", "kp_rent_avg": "Average rent per contract", "kp_rent_inc": "Average regular increase", "kp_rent_exp": "Contracts ending soon", "kp_rent_adv": "Advance stated (total)", "kp_rent_dep": "Deposit stated (total)",
        "kp_f_total": "Total stated fleet cost", "kp_f_maint": "Maintenance", "kp_f_fuel": "Fuel", "kp_f_cpk": "Cost per km (months with a distance)", "kp_f_veh": "Vehicles with a cost", "kp_f_claims": "Insurance claims (original amount)", "kp_f_due": "Service items due / soon",
        "kp_o_hours": "Total hours", "kp_o_wtd": "Weighted hours", "kp_o_night": "Night share", "kp_o_conc": "Top {n} employees' share", "kp_o_meals": "Meals", "kp_o_missions": "Missions", "kp_o_emp": "Employees with overtime",
    },
}


class C(BaseC):
    def __init__(self, lang):
        super().__init__(lang, T)


def _m(lang, p, short=False):
    return period_label(lang, (int(p[:4]), int(p[5:7])), short)


def _rng(lang, ps):
    if not ps:
        return "—"
    out, run = [], [ps[0]]
    for p in ps[1:]:
        y, m = int(run[-1][:4]), int(run[-1][5:7])
        if p == f"{y + (m == 12)}-{m % 12 + 1:02d}":
            run.append(p)
        else:
            out.append(run)
            run = [p]
    out.append(run)
    return "، ".join(_m(lang, g[0]) if len(g) == 1 else f"{_m(lang, g[0])} – {_m(lang, g[-1])}" for g in out)


def exclusions(c, A: dict, lang: str) -> list[dict]:
    """Everything that is left out of the official figures, or settled by evidence, or needs review — one row each, with its effect."""
    rows = []
    L = lambda ps: _rng(lang, ps)
    r, f, o = A["modules"]["rent"], A["modules"]["fleet"], A["modules"]["overtime"]
    if r:
        if r["partial"]:
            rows.append({"m": c.t("m_rent"), "i": c.t("e_rent_partial"), "s": c.t("st_not_comparable"), "e": c.t("ef_rent_partial"), "d": L(r["partial"])})
        if r["missing"]:
            rows.append({"m": c.t("m_rent"), "i": c.t("e_rent_missing"), "s": c.t("st_not_comparable"), "e": c.t("ef_rent_missing"), "d": L(r["missing"])})
        exc = next((s["exceptions"] for s in reversed(r["data"]["summaries"]) if s.get("exceptions")), [])
        for e in exc:
            kind = "excluded" if e["status"] == "excluded" else "resolved"
            vals = " | ".join(f"{g['n_sheets']} {c.t('c_sheet')}: " + "، ".join(f"{p}={v:g}" for p, v in list(g["months"].items())[:3]) for g in e["groups"][:3])
            rows.append({"m": c.t("m_rent"), "i": f"{c.t('e_rent_exc_' + kind)}: {e['name']}", "s": c.t("st_review") if kind == "excluded" else c.t("st_resolved"), "e": c.t("ef_rent_" + kind), "d": vals})
    if f:
        for p in f["partial"]:
            m = next(x for x in f["months"] if x["period"] == p)
            rows.append({"m": c.t("m_fleet"), "i": f"{c.t('e_fleet_partial')}: {_m(lang, p)}", "s": c.t("st_not_comparable"), "e": c.t("ef_fleet_partial"), "d": f"{m['active']}/{m['vehicles']} · {money2(m['total'])} {c.t('egp')}"})
        for cd in f["candidates"]:
            rows.append({"m": c.t("m_fleet"), "i": c.t("e_fleet_cand"), "s": c.t("st_review"), "e": c.t("ef_fleet_cand"), "d": " | ".join(cd["plates"])})
        ctl = [x for s in f["data"]["summaries"] for x in s.get("controls", []) if x.get("diff")] + [x for s in f["data"]["summaries"] for x in s.get("halfyear", []) if x.get("diff")]
        if ctl:
            rows.append({"m": c.t("m_fleet"), "i": c.t("ctl_vehicles"), "s": c.t("st_resolved"), "e": c.t("ef_ctl"), "d": str(len(ctl))})
    if o:
        for e in o["excluded"]:
            rows.append({"m": c.t("m_ot"), "i": f"{c.t('e_ot_excluded')}: {e['sheet']} → {_m(lang, e['period'])}", "s": c.t("st_excluded"), "e": c.t("ef_ot_excluded"), "d": e["reason"]})
        if o["missing"]:
            rows.append({"m": c.t("m_ot"), "i": c.t("e_ot_missing"), "s": c.t("st_not_comparable"), "e": c.t("ef_ot_missing"), "d": L(o["missing"])})
    return rows


def build_report(A: dict, data_by: dict, lang: str, admin: bool) -> ReportModel:
    c = C(lang)
    year = A["year"]
    th = A["thresholds"]
    L = lambda p: _m(lang, p)
    S = lambda p: _m(lang, p, True)
    egp = c.t("egp")
    r, f, o = A["modules"]["rent"], A["modules"]["fleet"], A["modules"]["overtime"]
    cb = A["combined"]
    rm = ReportModel(title=f"{c.t('title')} {year}", period_label=str(year), sections=[], lang=lang)
    files = [v["file"] for d in data_by.values() if isinstance(d, dict) and "versions" in d for v in d["versions"]]
    rm.subtitle = f"{len(files)} {c.t('c_file')}"
    rm.meta = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "file_name": "", "file_hash": "", "filters": {"active": {}, "options": {}, "dimensions": []}}
    excl = exclusions(c, A, lang)

    # ---------------------------------------------------------------- summary
    items = []
    if cb["common"]:
        items.append({"metric": "cost", "text": c.t("x_cost", m=_rng(lang, cb["common"]), v=money2(cb["total"]), r=money2(cb["rent"]), rp=pct(cb["rent_share"]), f=money2(cb["fleet"]), a=money2(cb["avg_month"]))})
        items.append({"metric": "scope", "text": c.t("x_scope", n=len(cb["common"]))})
        comb = [x for x in cb["rows"] if x["combined"] is not None]
        if len(comb) > 1:
            last = comb[-1]
            items.append({"metric": "mom", "text": c.t("x_mom", p=L(last["period"]), d=smoney(last["d"]), pc=spct(last["dpct"]))})
            items.append({"metric": "peak", "text": c.t("x_peak", pm=L(cb["peak"]["period"]), pv=money2(cb["peak"]["combined"]), lm=L(cb["low"]["period"]), lv=money2(cb["low"]["combined"]))})
    else:
        items.append({"metric": "nocommon", "text": c.t("x_nocommon", y=year)})
    if r:
        items.append({"metric": "rent", "text": c.t("x_rent", y=year, v=money2(r["total"]), n=len(r["complete"]), h=money2(r["hq"]))})
    else:
        items.append({"metric": "rent_na", "text": c.t("x_na_mod", m=c.t("m_rent"))})
    if f:
        items.append({"metric": "fleet", "text": c.t("x_fleet", y=year, v=money2(f["total"]), m=money2(f["maint"]), f=money2(f["fuel"]), n=sum(1 for v in f["vehicles"] if v["total"]))})
    else:
        items.append({"metric": "fleet_na", "text": c.t("x_na_mod", m=c.t("m_fleet"))})
    if o:
        items.append({"metric": "ot", "text": c.t("x_ot", y=year, h=f"{o['hours']:,.1f}", d=f"{o['day']:,.1f}", n=f"{o['night']:,.1f}", k=len(o["months"]))})
    else:
        items.append({"metric": "ot_na", "text": c.t("x_na_mod", m=c.t("m_ot"))})
    drv = [(c.t("m_rent") + " · " + (c.t("hq") if x["name"] == "المركز الرئيسي" else (x["name"] or c.t("unalloc"))), x["total"]) for x in A["drivers"]["rent_gov"][:1]] + \
          [(c.t("m_fleet") + " · " + x["name"], x["total"]) for x in A["drivers"]["fleet_cats"][:1]]
    if drv and cb["total"]:
        n, v = max(drv, key=lambda d: d[1])
        items.append({"metric": "driver", "text": c.t("x_driver", n=n, v=money2(v), s=pct(v / cb["total"] * 100))})
    if excl:
        items.append({"metric": "excl", "text": c.t("x_excl", n=len(excl))})
    rm.executive_summary = "\n".join("• " + i["text"] for i in items)
    rm.meta["summary_items"] = items
    sec = ReportSection(c.t("s_summary"), "summary")
    sec.kpis = [{"label": c.t("k_total"), "value": money2(cb["total"]) if cb["common"] else "—", "sub": f"{len(cb['common'])} {c.t('k_months')}" if cb["common"] else c.t("na")},
                {"label": c.t("k_rent"), "value": money2(cb["rent"]) if cb["common"] else "—", "sub": pct(cb["rent_share"]) if cb["common"] else ""},
                {"label": c.t("k_fleet"), "value": money2(cb["fleet"]) if cb["common"] else "—", "sub": egp}, {"label": c.t("k_avg"), "value": money2(cb["avg_month"]) if cb["common"] else "—", "sub": egp},
                {"label": c.t("k_ot"), "value": f"{o['hours']:,.1f}" if o else "—", "sub": c.t("hours") if o else c.t("na")}]
    sec.insights = [{"severity": "info", "text": i["text"], "metric": i["metric"]} for i in items]
    sec.insights += [{"severity": "info", "text": c.t(k)} for k in ("i_basis", "i_same", "i_personal")]
    rm.sections.append(sec)

    # ---------------------------------------------------------------- combined cost
    sec = ReportSection(c.t("s_cost"), "cost")
    rows = cb["rows"]
    comm = [x for x in rows if x["combined"] is not None]
    if comm:
        sec.charts.append({"type": "bar", "stacked": True, "title": c.t("ch_cost"), "x": [S(x["period"]) for x in comm], "series": [
            {"name": c.t("c_rent"), "values": [float(x["rent"]) for x in comm]}, {"name": c.t("c_fleet"), "values": [float(x["fleet"]) for x in comm]}]})
    if o:
        sec.charts.append({"type": "bar", "title": c.t("ch_ot"), "x": [S(m["period"]) for m in o["months"]], "series": [{"name": c.t("c_ot"), "values": [float(m["hours"]) for m in o["months"]]}]})
    stn = lambda x: " · ".join(f"{c.t('m_' + k)}: {c.t('st_' + x[k + '_state'])}" for k in ("rent", "fleet") if x[k + "_state"] != "ok")
    sec.tables.append({"key": "months", "title": c.t("t_cost"), "columns": [col("p", c.t("c_period")), col("r", c.t("c_rent"), "money"), col("f", c.t("c_fleet"), "money"), col("t", c.t("c_total"), "money"), col("d", c.t("c_d"), "smoney"),
                                                                           col("dp", c.t("c_dpct"), "spct"), col("o", c.t("c_ot"), "num"), col("n", c.t("c_note"))],
                       "rows": [{"p": L(x["period"]), "r": x["rent"], "f": x["fleet"], "t": x["combined"], "d": x.get("d"), "dp": x.get("dpct"), "o": x["overtime_hours"],
                                 "n": (c.t("large") if x.get("large") else "") + (" " if x.get("large") and stn(x) else "") + stn(x)} for x in rows], "pdf_rows": 40})
    sec.insights.append({"severity": "info", "text": c.t("i_nomoney_ot")})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- rent
    sec = ReportSection(c.t("s_rent"), "rent")
    if r:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_gov"), "x": [(c.t("hq") if g["name"] == "المركز الرئيسي" else (g["name"] or c.t("unalloc"))) for g in r["gov"][:12]],
                           "series": [{"name": c.t("c_amount"), "values": [float(g["total"]) for g in r["gov"][:12]]}]})
        sec.tables.append({"key": "rent_months", "title": c.t("t_rent_m"), "columns": [col("p", c.t("c_period")), col("v", c.t("c_total"), "money"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct"), col("n", c.t("c_note"))],
                           "rows": [({"p": L(m["period"]), "n": c.t("st_missing")} if not m["available"] else {"p": L(m["period"]), "v": m["total"], "d": m.get("d"), "dp": m.get("dpct"),
                                    "n": c.t("st_partial") if m["period"] in r["partial"] else (c.t("large") if m.get("large") else "")}) for m in r["months"]]})
        gt = r["total"]
        sec.tables.append({"key": "rent_gov", "title": c.t("t_rent_g"), "columns": [col("g", c.t("c_gov")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share_c"), "pct")],
                           "rows": [{"g": c.t("hq") if g["name"] == "المركز الرئيسي" else (g["name"] or c.t("unalloc")), "v": g["total"], "s": g["total"] / gt * 100 if gt else None} for g in r["gov"]]})
    else:
        sec.insights.append({"severity": "info", "text": c.t("x_na_mod", m=c.t("m_rent"))})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- fleet + vehicles
    sec = ReportSection(c.t("s_fleet"), "fleet")
    sec2 = ReportSection(c.t("s_vehicles"), "vehicles")
    if f:
        sec.charts.append({"type": "bar", "stacked": True, "title": c.t("t_fleet_m"), "x": [S(m["period"]) for m in f["months"]], "series": [
            {"name": c.t("c_maint"), "values": [float(m["maint"]) for m in f["months"]]}, {"name": c.t("c_fuel"), "values": [float(m["fuel"]) for m in f["months"]]}]})
        sec.tables.append({"key": "fleet_months", "title": c.t("t_fleet_m"), "columns": [col("p", c.t("c_period")), col("t", c.t("c_total"), "money"), col("m", c.t("c_maint"), "money"), col("f", c.t("c_fuel"), "money"), col("d", c.t("c_d"), "smoney"),
                                                                                        col("dp", c.t("c_dpct"), "spct"), col("n", c.t("c_note"))],
                           "rows": [{"p": L(m["period"]), "t": m["total"], "m": m["maint"], "f": m["fuel"], "d": m.get("d"), "dp": m.get("dpct"), "n": c.t("st_partial") if m["partial"] else (c.t("large") if m["large"] else "")} for m in f["months"]]})
        ct = sum(x["total"] for x in f["cats"])
        sec.tables.append({"key": "fleet_cats", "title": c.t("t_cats"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share_c"), "pct")],
                           "rows": [{"n": x["name"], "v": x["total"], "s": x["total"] / ct * 100 if ct else None} for x in f["cats"]]})
        ft = sum(v["total"] for v in f["vehicles"])
        sec2.tables.append({"key": "vehicles", "title": c.t("t_veh"), "columns": [col("p", c.t("c_plate")), col("ty", c.t("c_type")), col("m", c.t("c_months"), "int"), col("t", c.t("c_total"), "money"), col("s", c.t("c_share_c"), "pct"),
                                                                                  col("km", c.t("c_km"), "int"), col("cpk", c.t("c_cpk"), "money")],
                            "rows": [{"p": v["plate"], "ty": v["type"] or "—", "m": v["months"], "t": v["total"], "s": v["total"] / ft * 100 if ft else None, "km": v["km"], "cpk": v["cost_per_km"]} for v in f["vehicles"]], "pdf_rows": 30})
        sec2.insights.append({"severity": "info", "text": c.t("sig_cpk_note")})
    else:
        sec.insights.append({"severity": "info", "text": c.t("x_na_mod", m=c.t("m_fleet"))})
    rm.sections += [sec, sec2]

    # ---------------------------------------------------------------- overtime
    sec = ReportSection(c.t("s_ot"), "overtime")
    if o:
        sec.insights.append({"severity": "info", "text": c.t("i_nomoney_ot")})
        sec.tables.append({"key": "ot_months", "title": c.t("t_ot_m"), "columns": [col("p", c.t("c_period")), col("h", c.t("c_hours"), "num"), col("d", c.t("c_day"), "num"), col("n", c.t("c_night"), "num"), col("w", c.t("c_weighted"), "num"),
                                                                                   col("a", c.t("c_active"), "int"), col("x", c.t("c_dpct"), "spct")],
                           "rows": [{"p": L(m["period"]), "h": m["hours"], "d": m["day_hours"], "n": m["night_hours"], "w": m["weighted"], "a": m["active"], "x": m.get("dpct")} for m in o["months"]]})
        ecols = [col("code", c.t("c_code"))] + ([col("name", c.t("c_emp"))] if admin else []) + [col("m", c.t("c_months"), "int"), col("h", c.t("c_hours"), "num")]
        sec.tables.append({"key": "ot_emp", "title": c.t("t_ot_e"), "columns": ecols, "rows": [{"code": e["code"], **({"name": e["name"] or "—"} if admin else {}), "m": e["months"], "h": e["hours"]} for e in o["employees"]], "pdf_rows": 25})
    else:
        sec.insights.append({"severity": "info", "text": c.t("x_na_mod", m=c.t("m_ot"))})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- comparisons
    sec = ReportSection(c.t("s_compare"), "compare")
    cm = [x for x in rows if x["combined"] is not None and x.get("d") is not None]
    if cm:
        sec.tables.append({"key": "mom", "title": c.t("t_mom"), "columns": [col("p", c.t("c_period")), col("t", c.t("c_total"), "money"), col("d", c.t("c_d"), "smoney"), col("dp", c.t("c_dpct"), "spct")],
                           "rows": [{"p": L(x["period"]), "t": x["combined"], "d": x["d"], "dp": x["dpct"]} for x in cm]})
    def yoy(key, title, pairs):
        if pairs:
            sec.tables.append({"key": key, "title": title, "columns": [col("p", c.t("c_period")), col("a", c.t("c_this"), "num"), col("b", c.t("c_prev"), "num"), col("d", c.t("c_d"), "snum"), col("x", c.t("c_dpct"), "spct")],
                               "rows": [{"p": L(p), "a": a, "b": b, "d": a - b, "x": (a - b) / b * 100 if b else None} for p, a, b in pairs]})
        else:
            sec.insights.append({"severity": "info", "text": f"{title}: {c.t('i_yoy_na')}"})
    if r:
        yoy("yoy_rent", c.t("t_yoy_r"), [(x["period"], x["this"], x["prev"]) for x in r["yoy"]])
    if f:
        prev = {m["period"]: m for m in f["analysis"]["months"] if not m["partial"]}
        yoy("yoy_fleet", c.t("t_yoy_f"), [(m["period"], m["total"], prev[f"{year - 1}{m['period'][4:]}"]["total"]) for m in f["complete"] if f"{year - 1}{m['period'][4:]}" in prev])
    if o:
        prev = {m["period"]: m for m in o["analysis"]["avail"]}
        yoy("yoy_ot", c.t("t_yoy_o"), [(m["period"], m["hours"], prev[f"{year - 1}{m['period'][4:]}"]["hours"]) for m in o["months"] if f"{year - 1}{m['period'][4:]}" in prev])
    rm.sections.append(sec)

    # ---------------------------------------------------------------- drivers
    sec = ReportSection(c.t("s_drivers"), "drivers")
    D = A["drivers"]
    top = th["top_n"]
    tot = cb["total"] or 0
    shr = lambda v, base: (v / base * 100) if base else None
    allr = [(c.t("m_rent") + " · " + (c.t("hq") if g["name"] == "المركز الرئيسي" else (g["name"] or c.t("unalloc"))), g["total"]) for g in D["rent_gov"]]
    allf = [(c.t("m_fleet") + " · " + g["name"], g["total"]) for g in D["fleet_cats"]]
    both = sorted(allr[:top] + allf[:top], key=lambda x: -x[1])[:top]
    if both:
        sec.charts.append({"type": "bar", "horizontal": True, "title": c.t("ch_drv"), "x": [n for n, _v in both], "series": [{"name": c.t("c_amount"), "values": [float(v) for _n, v in both]}]})
        sec.tables.append({"key": "split", "title": c.t("t_split"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share"), "pct")],
                           "rows": [{"n": c.t("m_rent"), "v": cb["rent"], "s": shr(cb["rent"], tot)}, {"n": c.t("m_fleet") + " · " + c.t("c_maint"), "v": cb["maint"], "s": shr(cb["maint"], tot)},
                                    {"n": c.t("m_fleet") + " · " + c.t("c_fuel"), "v": cb["fuel"], "s": shr(cb["fuel"], tot)}]})
    gn = lambda g: c.t("hq") if g == "المركز الرئيسي" else (g or c.t("unalloc"))
    if D["rent_gov"]:
        sec.tables.append({"key": "d_rg", "title": c.t("t_d_rg"), "columns": [col("n", c.t("c_gov")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share"), "pct"), col("sc", c.t("c_share_c"), "pct")],
                           "rows": [{"n": gn(g["name"]), "v": g["total"], "s": shr(g["total"], tot), "sc": shr(g["total"], cb["rent"])} for g in D["rent_gov"][:top]]})
        sec.tables.append({"key": "d_rc", "title": c.t("t_d_rc"), "columns": [col("n", c.t("c_name")), col("g", c.t("c_gov")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share"), "pct")],
                           "rows": [{"n": x["name"], "g": gn(x["governorate"]), "v": x["total"], "s": shr(x["total"], tot)} for x in D["rent_contracts"][:top]]})
    if D["fleet_cats"]:
        sec.tables.append({"key": "d_fc", "title": c.t("t_d_fc"), "columns": [col("n", c.t("c_name")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share"), "pct"), col("sc", c.t("c_share_c"), "pct")],
                           "rows": [{"n": x["name"], "v": x["total"], "s": shr(x["total"], tot), "sc": shr(x["total"], cb["fleet"])} for x in D["fleet_cats"][:top]]})
        sec.tables.append({"key": "d_fv", "title": c.t("t_d_fv"), "columns": [col("n", c.t("c_plate")), col("v", c.t("c_amount"), "money"), col("s", c.t("c_share"), "pct"), col("sc", c.t("c_share_c"), "pct")],
                           "rows": [{"n": x["plate"], "v": x["total"], "s": shr(x["total"], tot), "sc": shr(x["total"], cb["fleet"])} for x in D["fleet_vehicles"][:top]]})
    if not both:
        sec.insights.append({"severity": "info", "text": c.t("x_nocommon", y=year)})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- biggest moves
    sec = ReportSection(c.t("s_moves"), "moves")
    n = th["move_n"]
    def mv(key, title, rows_, kind):
        if not rows_:
            return
        if kind == "rent":
            cols = [col("n", c.t("c_name")), col("g", c.t("c_gov")), col("a", c.t("c_old"), "money"), col("b", c.t("c_new"), "money"), col("d", c.t("c_d"), "smoney"), col("x", c.t("c_pct"), "spct")]
            data = [{"n": x["name"], "g": gn(x["governorate"]), "a": x["first"], "b": x["last"], "d": x["d"], "x": x["pct"]} for x in rows_[:n]]
        elif kind == "fleet":
            cols = [col("n", c.t("c_plate")), col("p", c.t("c_period")), col("a", c.t("c_old"), "money"), col("b", c.t("c_new"), "money"), col("d", c.t("c_d"), "smoney"), col("x", c.t("c_pct"), "spct")]
            data = [{"n": x["plate"], "p": L(x["to"]), "a": x["old"], "b": x["new"], "d": x["d"], "x": x["pct"]} for x in rows_[:n]]
        else:
            cols = [col("n", c.t("c_emp") if admin else c.t("c_code")), col("p", c.t("c_period")), col("a", c.t("c_old"), "num"), col("b", c.t("c_new"), "num"), col("d", c.t("c_d"), "snum"), col("x", c.t("c_pct"), "spct")]
            data = [{"n": (x["name"] or x["code"]) if admin else x["code"], "p": L(x["to"]), "a": x["old"], "b": x["new"], "d": x["d"], "x": x["pct"]} for x in rows_[:n]]
        sec.tables.append({"key": key, "title": title, "columns": cols, "rows": data})
    if r:
        mv("m_rr", c.t("t_m_rr"), r["rises"], "rent")
        mv("m_rf", c.t("t_m_rf"), r["falls"], "rent")
    if f:
        mv("m_fr", c.t("t_m_fr"), f["rises"], "fleet")
        mv("m_ff", c.t("t_m_ff"), f["falls"], "fleet")
    if o:
        mv("m_or", c.t("t_m_or"), o["rises"], "ot")
        mv("m_of", c.t("t_m_of"), o["falls"], "ot")
    rm.sections.append(sec)

    # ---------------------------------------------------------------- signals
    sec = ReportSection(c.t("s_signals"), "signals")
    sec.insights.append({"severity": "info", "text": c.t("i_signals")})
    k = th["signal_n"]
    if r and r["expiring"]:
        sec.insights.append({"severity": "info", "text": c.t("sig_exp_note", w=r["windows"][0], n=r["expiring_long"], x=r["windows"][1])})
        sec.tables.append({"key": "sig_exp", "title": c.t("t_sig_exp"), "columns": [col("n", c.t("c_name")), col("g", c.t("c_gov")), col("e", c.t("c_end")), col("v", c.t("c_cur"), "money")],
                           "rows": [{"n": x["name"], "g": gn(x["governorate"]), "e": x["end"].isoformat() if x["end"] else "—", "v": x["last"]} for x in sorted(r["expiring"], key=lambda x: -(x["last"] or 0))[:k]]})
    if r:
        inc = sorted((s for s in r["steps"] if s["pct"] and s["pct"] > 0 and not s["large"]), key=lambda s: -s["pct"])[:k]
        if inc:
            sec.tables.append({"key": "sig_inc", "title": c.t("t_sig_inc"), "columns": [col("n", c.t("c_name")), col("g", c.t("c_gov")), col("p", c.t("c_period")), col("a", c.t("c_old"), "money"), col("b", c.t("c_new"), "money"), col("x", c.t("c_pct"), "spct")],
                               "rows": [{"n": s["name"], "g": gn(s["governorate"]), "p": L(s["period"]), "a": s["old"], "b": s["new"], "x": s["pct"]} for s in inc]})
    if f:
        cpk = sorted((v for v in f["vehicles"] if v["cost_per_km"]), key=lambda v: -v["cost_per_km"])[:k]
        if cpk:
            sec.tables.append({"key": "sig_cpk", "title": c.t("t_sig_cpk"), "columns": [col("n", c.t("c_plate")), col("cpk", c.t("c_cpk"), "money"), col("km", c.t("c_km"), "int"), col("t", c.t("c_total"), "money")],
                               "rows": [{"n": v["plate"], "cpk": v["cost_per_km"], "km": v["km"], "t": v["total"]} for v in cpk]})
        if f["outliers"]:
            sec.tables.append({"key": "sig_out", "title": c.t("t_sig_out"), "columns": [col("n", c.t("c_plate")), col("p", c.t("c_period")), col("t", c.t("c_total"), "money"), col("m", c.t("c_median"), "money"), col("f", c.t("c_factor"), "num")],
                               "rows": [{"n": x["plate"], "p": L(x["period"]), "t": x["total"], "m": x["median"], "f": x["factor"]} for x in f["outliers"][:k]]})
        cl = [x for x in f["claims"] if x.get("company_share")]
        if cl:
            sec.tables.append({"key": "sig_claims", "title": c.t("t_sig_claims"), "columns": [col("n", c.t("c_claim")), col("o", c.t("c_orig"), "money"), col("c", c.t("c_company"), "money")],
                               "rows": [{"n": x["desc"], "o": x.get("original"), "c": x.get("company_share")} for x in cl]})
    if o and o["high"]:
        sec.tables.append({"key": "sig_ot", "title": c.t("t_sig_ot"), "columns": [col("n", c.t("c_emp") if admin else c.t("c_code")), col("p", c.t("c_period")), col("h", c.t("c_hours"), "num"), col("f", c.t("c_factor"), "num")],
                           "rows": [{"n": (x["name"] or x["code"]) if admin else x["code"], "p": L(x["period"]), "h": x["hours"], "f": x["factor"]} for x in o["high"][:k]]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- KPIs per module
    sec = ReportSection(c.t("s_kpis"), "kpis")
    kp = []
    if r:
        t = r["analysis"]["totals"]
        kp += [(c.t("m_rent"), c.t("kp_rent_total"), money2(r["total"]) + " " + egp), (c.t("m_rent"), c.t("kp_rent_n"), f"{t['with_value_last']} / {t['contracts']}"),
               (c.t("m_rent"), c.t("kp_rent_avg"), money2(t["avg_per_contract"]) + " " + egp if t["avg_per_contract"] else "—"), (c.t("m_rent"), c.t("kp_rent_inc"), pct(t["avg_up_pct"])),
               (c.t("m_rent"), c.t("kp_rent_exp"), f"{t['expiring']} ({t['expiring_window']}) · {t['expiring_long']} ({t['expiring_long_window']})"), (c.t("m_rent"), c.t("kp_rent_adv"), money2(t["advance_total"]) + " " + egp),
               (c.t("m_rent"), c.t("kp_rent_dep"), money2(t["deposit_total"]) + " " + egp)]
    if f:
        t = f["analysis"]["totals"]
        kp += [(c.t("m_fleet"), c.t("kp_f_total"), money2(f["total"]) + " " + egp), (c.t("m_fleet"), c.t("kp_f_maint"), money2(f["maint"]) + " " + egp), (c.t("m_fleet"), c.t("kp_f_fuel"), money2(f["fuel"]) + " " + egp),
               (c.t("m_fleet"), c.t("kp_f_cpk"), money2(t["cost_per_km"]) + " " + egp if t["cost_per_km"] is not None else "—"), (c.t("m_fleet"), c.t("kp_f_veh"), str(sum(1 for v in f["vehicles"] if v["total"]))),
               (c.t("m_fleet"), c.t("kp_f_claims"), money2(sum(x.get("original") or 0 for x in f["claims"])) + " " + egp), (c.t("m_fleet"), c.t("kp_f_due"), str(t["due_soon"]))]
    if o:
        oa = o["analysis"]["totals"]
        kp += [(c.t("m_ot"), c.t("kp_o_hours"), f"{o['hours']:,.1f}"), (c.t("m_ot"), c.t("kp_o_wtd"), f"{o['weighted']:,.1f}"), (c.t("m_ot"), c.t("kp_o_night"), pct(o["night"] / o["hours"] * 100) if o["hours"] else "—"),
               (c.t("m_ot"), c.t("kp_o_conc", n=o["conc_n"]), pct(o["top_share"])), (c.t("m_ot"), c.t("kp_o_meals"), f"{o['meals']:,.0f}"), (c.t("m_ot"), c.t("kp_o_missions"), f"{o['missions']:,.0f}"),
               (c.t("m_ot"), c.t("kp_o_emp"), str(sum(1 for e in o["employees"] if e["hours"])))]
    sec.tables.append({"key": "kpis", "title": c.t("t_kpi"), "columns": [col("m", c.t("c_module")), col("k", c.t("c_kpi")), col("v", c.t("c_value"))], "rows": [{"m": a_, "k": b_, "v": v_} for a_, b_, v_ in kp]})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- quality + exceptions
    sec = ReportSection(c.t("s_quality"), "quality")
    sec.tables.append({"key": "exclusions", "title": c.t("t_excl"), "columns": [col("m", c.t("c_module")), col("i", c.t("c_item")), col("s", c.t("c_status")), col("e", c.t("c_effect")), col("d", c.t("c_detail"))],
                       "rows": excl, "pdf_rows": 40})
    irows = []
    for key, label in (("rent", c.t("m_rent")), ("vehicles", c.t("m_fleet")), ("overtime", c.t("m_ot"))):
        d = data_by.get(key)
        if d:
            for i in merged_issues(d["summaries"]):
                irows.append({"m": label, "msg": i["message"], "sev": c.s.get("sev_" + i["severity"], i["severity"]), "n": i["count"], "ex": " | ".join(i["examples"][:3])})
    sec.tables.append({"key": "issues", "title": c.t("t_issues"), "columns": [col("m", c.t("c_module")), col("msg", c.t("c_issue")), col("sev", c.t("c_sev")), col("n", c.t("c_n"), "int"), col("ex", c.t("c_ex"))], "rows": irows, "pdf_rows": 40})
    srows = [{"n": f"annual.{k}", "v": v, "o": ""} for k, v in th.items()]
    for key, label in (("rent", "rent"), ("vehicles", "vehicles"), ("overtime", "overtime")):
        mth = A["module_thresholds"].get(key)
        if mth:
            srows += [{"n": f"{label}.{k}", "v": v, "o": ""} for k, v in mth.items()]
    sec.tables.append({"key": "settings", "title": c.t("t_settings"), "columns": [col("n", c.t("c_set")), col("v", c.t("c_value"))], "rows": srows})
    rm.sections.append(sec)

    # ---------------------------------------------------------------- versions
    sec = ReportSection(c.t("s_versions"), "versions")
    vrows, crows = [], []
    for key, label in (("rent", c.t("m_rent")), ("vehicles", c.t("m_fleet")), ("overtime", c.t("m_ot"))):
        d = data_by.get(key)
        if not d:
            continue
        for i, v in enumerate(d["versions"], 1):
            vrows.append({"m": label, "f": f"#{i} · {v['file']}", "up": v["uploaded_at"], "fr": v["from"] or "—", "to": v["to"] or "—", "n": v["records"], "a": v["added"], "x": v["dropped"], "c": v["changed"]})
        fld = lambda x: c.s.get("fld_" + x, x[4:] if x.startswith("cat:") else x)
        for ch in sorted(d["changes"], key=lambda x: (x["to_dataset"], str(x["period"] or "")), reverse=True)[:15]:
            who = ch["label"] or ch["key"]
            crows.append({"m": label, "i": who, "p": L(ch["period"]) if ch["period"] else "—", "f": fld(ch["field"]), "a": ch["old"], "b": ch["new"]})
    sec.tables.append({"key": "versions", "title": c.t("t_versions"), "columns": [col("m", c.t("c_module")), col("f", c.t("c_file")), col("up", c.t("c_up")), col("fr", c.t("c_from")), col("to", c.t("c_to")), col("n", c.t("c_records"), "int"),
                                                                                col("a", c.t("c_added"), "int"), col("x", c.t("c_dropped"), "int"), col("c", c.t("c_changed"), "int")], "rows": vrows})
    if crows:
        sec.tables.append({"key": "changes", "title": c.t("t_changes"), "columns": [col("m", c.t("c_module")), col("i", c.t("c_item")), col("p", c.t("c_period")), col("f", c.t("c_field")), col("a", c.t("c_old")), col("b", c.t("c_new"))],
                           "rows": [{**x, "a": _fv(x["a"]), "b": _fv(x["b"])} for x in crows], "pdf_rows": 30})
    rm.sections.append(sec)
    _ = (money, c.t("x_noforec"))
    return rm


def _fv(v):
    return "—" if v is None else (f"{v:,.2f}".rstrip("0").rstrip(".") if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))
