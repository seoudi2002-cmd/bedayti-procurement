"""Synthetic workbooks mimicking the *shape* of the rent, overtime and vehicle files (no real data)."""
import io
import re
import zipfile
from datetime import datetime
from functools import lru_cache

from openpyxl import Workbook

RENT_HEAD = ["م", "المركز / المدينة", "المقدم", "التامين", "بداية العقد", "نهاية العقد", "القيمة الايجارية بالعقد", "يناير 2025", "فبراير 2025", "مارس 2025"]


def _save(wb, cache: dict | None = None) -> bytes:
    """Save; `cache` = {sheet title: {cell: value}} injects cached results for formula cells (a workbook writer does not compute them)."""
    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()
    if not cache:
        return data
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            raw = src.read(item.filename)
            for i, title in enumerate(wb.sheetnames, start=1):
                if item.filename == f"xl/worksheets/sheet{i}.xml" and title in cache:
                    xml = raw.decode("utf-8")
                    for cell, val in cache[title].items():
                        xml = re.sub(rf'(<c r="{cell}"[^>]*><f>[^<]*</f>)<v></v>', lambda m, v=val: f"{m.group(1)}<v>{v}</v>", xml)
                    raw = xml.encode("utf-8")
            dst.writestr(item, raw)
    return out.getvalue()


@lru_cache(maxsize=None)
def rent_workbook(version: int = 1) -> bytes:
    """Two governorate sheets repeating one master list (rows 3-6), each footer adding up *its* contracts with a formula, plus Head Office.
    v2: contract A is increased in March and a new contract appears in the Menoufia footer."""
    wb = Workbook()
    wb.remove(wb.active)
    a_mar = 1210 if version == 2 else 1100
    master = [
        [1, "الزقاريق ( الشرقية )", "_____", 5000, "01/01/2024", "31/12/2030", 1000, 1100, 1100, a_mar],
        [2, "أبو حماد ( الشرقية )", 3000, "_____", "01/02/2024", "31/03/2025", 2000, 2200, "_____", 2200],
        [3, "منوف ( المنوفية )", "_____", "_____", "01/01/2024", "30/09/2026", 500, 550, 550, 550],
        [4, "فرع بلا محافظة", "_____", "_____", "01/01/2024", "31/9/2030", 300, 330, 330, 330],
    ]
    for gov in ("الشرقية", "المنوفية"):
        ws = wb.create_sheet(gov)
        ws.append([gov])
        ws.append(RENT_HEAD)
        for i, r in enumerate(master):
            r = list(r)
            if gov == "المنوفية" and i == 0:
                r[9] = 999                                     # a stale copy of contract A in a sheet that does not own it
            ws.append(r)
        ws.append([None, None, None, None, None, None, None, "=SUM(H3:H6)", "=SUM(I3:I6)", "=SUM(J3:J6)"])     # master total (no name, no '+')
        if gov == "المنوفية":
            ws.append([5, "بنها ( المنوفية )", "_____", "_____", datetime(2025, 3, 1), "28/02/2032", 400, None, None, 440])    # footer: this sheet's own contract
            ws.append([None, "اجمالي محافظة المنوفية", None, None, None, None, None, "=SUM(H5+H8)", "=SUM(I5+I8)", "=SUM(J5+J8)"])
        else:
            ws.append([None, "اجمالي محافظة الشرقية", None, None, None, None, None, "=SUM(H3+H4)", "=SUM(I3+I4)", "=SUM(J3+J4)"])
    hq = wb.create_sheet("المركز الرئيسي")
    hq.append(["بيان العقود"])
    hq.append(["المركز / المدينة / المحافظة", "المقدم", "التامين", "المالك", "بداية العقد", "نهاية العقد", "يناير 2025", "فبراير 2025", "مارس 2022"])
    hq.append(["العجوزة د3", "_____", 900, "مالك أ", datetime(2024, 1, 3), "28/02/2030", 700, 700, 770])
    hq.append(["الإجمالي المسدد", None, None, "الإجمالي", None, None, 700, 700, 770])
    cache = {"الشرقية": {"H8": 3300, "I8": 1100, "J8": a_mar + 2200}, "المنوفية": {"H9": 550, "I9": 550, "J9": 991}}      # Menoufia's March total is stated one off (990 + 1)
    return _save(wb, cache)


OT_HEAD2 = ["الكود", "الاسم ", "مأموريات ", None, "وجبات", "الساعات الإضافية ", None, None, None, "الإجمالي ", "مثل الاجر ", "الاجمالي * 2"]
OT_HEAD3 = [None, None, "نهاري ", "ليلي ", None, "نهاري", None, "ليلي ", None, None, None, None]


def _ot_sheet(wb, name, title, rows):
    ws = wb.create_sheet(name)
    ws["C1"] = title
    ws.append(OT_HEAD2)
    ws.append(OT_HEAD3)
    for code, nm, vals in rows:
        ws.append([code, nm, *vals] if vals else [code, nm])
    return ws


@lru_cache(maxsize=None)
def overtime_workbook(corrected: bool = False) -> bytes:
    """Jan, Feb, and a third sheet named March whose title and data repeat February; plus an annual `report` sheet adding the months by formula.
    corrected: a different February figure for employee 10."""
    wb = Workbook()
    wb.remove(wb.active)
    jan = [(10, "موظف أول", [1, 1, 20, 20, 27, 10, 17, 44, 0, 0]), (11, "موظف ثان", [0, 0, 18, 10, 13.5, 5, 8.5, 22, 1, 2]), (12, "موظف ثالث", None)]
    dh = 44 if corrected else 40
    feb = [(10, "موظف أول", [0, 2, 21, dh, round(dh * 1.35, 2), 12, 20.4, round(dh * 1.35 + 20.4, 2), 0, 0]), (11, "موظف ثان", [0, 0, 18, 10, 13.5, 0, 0, 13.5, 0, 0]), (12, "موظف ثالث", None)]
    _ot_sheet(wb, "يناير", "بيان بالاجر الإضافي - شهر يناير 2025", jan)
    _ot_sheet(wb, "فبراير", "بيان بالاجر الإضافي - شهر فبراير2025", feb)
    _ot_sheet(wb, "مارس", "بيان بالاجر الإضافي - شهر فبراير2025", feb)
    rep = wb.create_sheet("report")
    rep["A1"] = "بيان بالاجر الإضافي"
    rep.append(["الكود", "الاسم ", "مأموريات ", None, "وجبات", "الساعات الإضافية ", None, None, None, "الإجمالي ", "مثل الاجر ", "الاجمالي * 2"])
    rep.append([None, None, "نهاري ", "ليلي ", None, "نهاري", 1.35, "ليلي ", 1.7, "الإجمالي", None, None])
    for r, code, nm in ((4, 10, "موظف أول"), (5, 11, "موظف ثان")):
        rep.append([code, nm] + [f"=يناير!{c}{r}+فبراير!{c}{r}+مارس!{c}{r}" for c in "CDEFGHIJKL"])
    rep.append(["الاجمالي", None, 1, 5, 116, 130, 175.5, 39, 66.3, 241.8, 1, 2])         # stated annual totals: they include the repeated sheet
    return _save(wb)


def _repairs_sheet(wb, month_name, month_ar, rows, total, qty_price=20.0):
    """Rows: (plate, type, oil, maint, other, toll, fuel, km, note). Totals are written as numbers (a workbook writer cannot cache formula results);
    the fuel quantity is a formula =cost/price like the real file, so its price is readable but its value is not cached."""
    ws = wb.create_sheet(month_name)
    ws["A1"] = f"بيان الاصلاحات سيارات المركز الرئيسي عن شهر {month_ar} 2026"
    ws.append(["م", "رقم السيارة", "نوع السيارة", "الصيانات جم", None, "اخري", "بوابات رسوم", "اجمالي تكلفة الصيانات", "اجمالي تكلفة الوقود جم", "اجمالى كمية الوقود لتر", "الاجمالى العام جم", "المسافة المقطوعة كم", "ملاحظات"])
    ws.append([None, None, None, "زيوت", "صيانة", "اخري", None, None, None, None, None, None, None])
    ws.append([None, None, None, None, None, "تكييف", None, None, None, None, None, None, None])
    for i, (plate, vt, oil, maint, other, toll, fuel, km, note) in enumerate(rows, start=5):
        m = sum(x or 0 for x in (oil, maint, other, toll))
        ws.append([i - 4, plate, vt, oil, maint, other, toll, m, fuel, f"=I{i}/{qty_price}" if fuel is not None else None, m + (fuel or 0), km, note])
    if total is not None:
        ws.append([None] * 10 + [total])
    return ws


JAN = [("س ص 1111", "تويوتا", 100, None, None, 20, 1000, 800, None), ("س ص 2222", "اودي", None, 5000, None, None, 2000, 1500, "إصلاح")]
FEB = [("س ص 1111", "تويوتا", None, 700, None, 10, 1100, 900, None), ("س ص 2222", "اودي", 100, None, 300, None, 2100, 1600, None)]
JAN_TOTAL = 1120 + 7000          # the vehicle rows' own sum
FEB_TOTAL = 1810 + 2500


@lru_cache(maxsize=None)
def repairs_workbook(corrected: bool = False) -> bytes:
    """Jan and Feb for two vehicles + a half-year sheet (one vehicle's total off) with an insurance-claim side table. Jan's stated total row is one off.
    corrected: a different Feb repair for the first vehicle (a corrected file)."""
    feb = [("س ص 1111", "تويوتا", None, 900, None, 10, 1100, 900, None), FEB[1]] if corrected else FEB
    wb = Workbook()
    wb.remove(wb.active)
    _repairs_sheet(wb, "يناير", "يناير", JAN, JAN_TOTAL + 1)
    _repairs_sheet(wb, "فبراير", "فبراير", feb, None)
    ws = wb.create_sheet("اجمالي نصف عام 2026")
    ws.append(["بيان الاصلاحات"] + [None] * 24 + ["تحت حساب التأمين", "الشهر", "اصل المبلغ", "نسبة تحمل التأمين", "نسبة تحمل الشركة"])
    ws.append(["م", "رقم السيارة", "نوع السيارة"] + [None] * 17 + ["الاجمالى العام جم"] + [None] * 4 + ["زجاج", "يناير", 1000, 700, 300])
    ws.append([1, "س ص 1111", "تويوتا"] + [None] * 17 + [9999])
    ws.append([2, "س ص 2222", "اودي"] + [None] * 17 + [9500])
    ws.append([None] * 18 + ["الإجمالي العام", None, 19499])
    return _save(wb)


def _usage_book(months, odo0=1000):
    wb = Workbook()
    wb.remove(wb.active)
    start = odo0
    for i, name in enumerate(months, start=1):
        ws = wb.create_sheet(name)
        ws["A1"] = "قطاع الشئون الادارية"
        ws["C3"] = "تقرير عن تنظيم استخدام السيارات عن شهر"
        ws["G3"] = datetime(2026, 1, i)
        ws["C4"], ws["G4"] = "إجمالي المسافة المقطوعة", 150
        ws["C5"], ws["G5"] = "إجمالي كمية الوقود المستهلكة", 15
        ws["C6"], ws["G6"] = "معدل استهلاك السيارة كم / لتر", 10
        ws["C7"], ws["G7"] = "عدد مرات تغيير الزيت", 1
        ws["A9"], ws["D9"], ws["E9"] = "ماركة السيارة / بيجو", "رقم السيارة / ", "ع ن 3333"
        ws["A10"], ws["B10"], ws["D10"] = "الأيام", "العداد", "المسافة المقطوعة"
        for d, km in ((1, 100), (2, 50)):
            ws.cell(11 + d, 1, d)
            ws.cell(11 + d, 2, start)
            ws.cell(11 + d, 3, start + km)
            ws.cell(11 + d, 4, km)
            start += km
        ws.cell(14, 4, 150)
    return _save(wb)


@lru_cache(maxsize=None)
def usage_book() -> bytes:
    return _usage_book(["يناير", "فبراير"])


def _card_book(km_by_sheet):
    wb = Workbook()
    wb.remove(wb.active)
    for name, (date_txt, km) in km_by_sheet.items():
        ws = wb.create_sheet(name)
        ws["A5"] = f"كارت صيانة السيارات العاملة بالمركز الرئيسي ({date_txt} )"
        ws["A7"], ws["B7"], ws["C7"], ws["D7"], ws["E7"], ws["F7"] = "م", "رقم السيارة", "نوع السيارة", "قائد السيارة", "كم الحالى", "غيار الزيت"
        ws["F8"], ws["G8"], ws["H8"] = "السابق", "الحالى", "كم المتبقى"
        ws.append([])
        ws["A9"], ws["B9"], ws["C9"], ws["D9"], ws["E9"] = 1, 3333, "بيجو", "متنوع", km
        ws["F9"], ws["G9"], ws["H9"] = 20000, 30000, (30000 - km) if km else 30000
    return _save(wb)


@lru_cache(maxsize=None)
def card_book() -> bytes:
    return _card_book({"يناير": ("2026/01/01", 29500), "فبراير": ("2026/02/01", 29900), "مارس": ("2026/03/01", 0)})
