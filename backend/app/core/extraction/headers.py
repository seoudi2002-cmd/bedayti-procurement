"""Document header fields (PO number, date, supplier, requisition, ...) from page text lines.

Each field comes back as {"value", "raw", "confidence", "page"}: `raw` is the text exactly as read. Nothing is
filled in when the text does not support it.
"""
import re
from dataclasses import dataclass
from datetime import date

from app.core.cleaning.normalizers import normalize_text

_DATE_YMD = re.compile(r"(20\d{2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})")
_DATE_DMY = re.compile(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(20\d{2})")


@dataclass
class TextLine:
    text: str
    conf: float  # 0-1
    page: int


def lines_from_ocr(page_no: int, ocr_page) -> list[TextLine]:
    by_line: dict[tuple, list] = {}
    for w in ocr_page.words:
        by_line.setdefault(w.line_key, []).append(w)
    return [TextLine(" ".join(w.text for w in ws), sum(max(w.conf, 0) for w in ws) / len(ws) / 100, page_no)
            for ws in by_line.values()]


def lines_from_text(page_no: int, text: str, conf: float = 1.0) -> list[TextLine]:
    return [TextLine(t.strip(), conf, page_no) for t in text.splitlines() if t.strip()]


def _field(value, raw, conf, page) -> dict:
    return {"value": value, "raw": raw, "confidence": round(float(conf), 3), "page": page}


def parse_date_text(text: str) -> date | None:
    t = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    m = _DATE_YMD.search(t)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = _DATE_DMY.search(t)
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    return None


def _first_int(text: str, lo: int = 1, hi: int = 99999) -> tuple[int, str] | None:
    t = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    # a number written in brackets - "( 32 )" - is the document number; stray digits elsewhere on a noisy line are not
    br = re.search(r"[(\[]\s*(\d{1,5})\s*[)\]()]", t)
    if br and lo <= int(br.group(1)) <= hi and not (1990 <= int(br.group(1)) <= 2100):
        return int(br.group(1)), br.group(1)
    for m in re.finditer(r"(?<!\d)(\d{1,5})(?!\d)", t):
        v = int(m.group(1))
        if lo <= v <= hi and not (1990 <= v <= 2100):
            return v, m.group(1)
    return None


def extract_po_header(lines: list[TextLine]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ln in lines:
        n = normalize_text(ln.text)
        if "po_number" not in out and re.search(r"شرا[ءه]", n) and re.search(r"رقم|رشم|رفم", n) and not re.search(r"تابع", n):
            hit = _first_int(ln.text)
            if hit:
                out["po_number"] = _field(str(hit[0]), ln.text, ln.conf, ln.page)
        if "po_date" not in out and re.search(r"التاريخ", n):
            d = parse_date_text(ln.text)
            if d:
                out["po_date"] = _field(d.isoformat(), ln.text, ln.conf, ln.page)
        if "requisition_no" not in out and re.search(r"رقم الاشعار|رقم الإشعار|الاشعار\s*[:(]", n):
            hit = _first_int(ln.text)
            if hit:
                out["requisition_no"] = _field(str(hit[0]), ln.text, ln.conf, ln.page)
        if "supplier_register_no" not in out and re.search(r"سجل\s*مورد", n):
            hit = _first_int(ln.text)
            if hit:
                out["supplier_register_no"] = _field(str(hit[0]), ln.text, ln.conf, ln.page)
        if "supplier_name" not in out and re.search(r"السادة", n) and "لجنه" not in n and "المشتريات" not in n:
            name = re.split(r"[:：]", ln.text, maxsplit=1)
            cand = (name[-1] if len(name) > 1 else ln.text).strip(" :-.‎‏")
            cand = re.sub(r"^(?:ال)?سادة\s*/?\s*", "", cand).strip()
            cand = re.sub(r"^إلى\s*", "", cand).strip()
            if 2 < len(cand) < 80:
                out["supplier_name"] = _field(cand, ln.text, ln.conf, ln.page)
        if "requesting_unit" not in out and re.search(r"الجهه الطالبه", n):
            name = re.split(r"[:：]", ln.text, maxsplit=1)
            cand = (name[-1] if len(name) > 1 else "").strip()
            if cand:
                out["requesting_unit"] = _field(cand, ln.text, ln.conf, ln.page)
        if "purchase_method" not in out and re.search(r"طريقه الشراء", n):
            name = re.split(r"[:：]", ln.text, maxsplit=1)
            cand = (name[-1] if len(name) > 1 else "").strip()
            if cand:
                out["purchase_method"] = _field(cand, ln.text, ln.conf, ln.page)
    return out


def extract_memo_header(lines: list[TextLine]) -> dict[str, dict]:
    """Committee / payment-request memos (Word or scanned)."""
    out: dict[str, dict] = {}
    for ln in lines:
        n = normalize_text(ln.text)
        if "memo_date" not in out and re.search(r"التاريخ", n):
            d = parse_date_text(ln.text)
            if d:
                out["memo_date"] = _field(d.isoformat(), ln.text, ln.conf, ln.page)
        if "subject" not in out and re.search(r"الموضوع", n):
            out["subject"] = _field(re.split(r"[:：]", ln.text, maxsplit=1)[-1].strip(), ln.text, ln.conf, ln.page)
        if "requisition_no" not in out and re.search(r"اشعار\s*ال?احتياج\s*رقم", n):
            m = re.search(r"رقم\s*\(?\s*([\d٠-٩]+)", ln.text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            if m:
                out["requisition_no"] = _field(str(int(m.group(1))), ln.text, ln.conf, ln.page)
        if "po_number" not in out and re.search(r"(?:امر|أمر)\s*ال?شرا[ءه]\s*رقم", n):
            m = re.search(r"رقم\s*\(?\s*([\d٠-٩]+)", ln.text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            if m:
                out["po_number"] = _field(str(int(m.group(1))), ln.text, ln.conf, ln.page)
        if "amount_text" not in out and re.search(r"بمبلغ", n):
            m = re.search(r"([\d][\d,\.]*)\s*جم", ln.text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            if m:
                out["stated_total"] = _field(m.group(1).replace(",", ""), ln.text, ln.conf, ln.page)
                out["amount_text"] = _field(ln.text, ln.text, ln.conf, ln.page)
    return out
