"""Reader for the supplier's Egyptian e-invoice (ETA) PDF.

The PDF stores Arabic in visual order (presentation forms, reversed) with Arabic-Indic digits and splits long numbers
across lines inside a table cell. Lines are rebuilt from word positions (columns come from the table header), numbers
are re-joined, and every invoice line is re-checked arithmetically. Values are kept as read; nothing is corrected."""
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.core.cleaning.normalizers import normalize_text

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫،", "0123456789,.,")
_PERSIAN = str.maketrans({"ی": "ي", "ھ": "ه", "ک": "ك", "ۀ": "ه"})
_BIDI = re.compile("[‪-‮‎‏⁦-⁩]")
_LETTERS = re.compile("[ء-ي]")
PACKAGES = (1000, 2000, 3000, 5000, 10000)


class UnrecognisedInvoice(ValueError):
    pass


@dataclass
class InvoiceLine:
    line_no: int
    page: int
    description: str
    kind: str                 # rent | excess | other
    packages: list[int]
    color: bool
    a3: bool
    printers: bool
    qty: Decimal | None
    unit_price: Decimal | None
    sales_total: Decimal | None
    net_total: Decimal | None
    vat_value: Decimal | None
    vat_rate: Decimal | None
    wht_value: Decimal | None
    wht_rate: Decimal | None
    total: Decimal | None
    period_from: date | None = None
    period_to: date | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class Invoice:
    internal_no: str | None = None
    electronic_id: str | None = None
    issued_on: date | None = None
    status: str | None = None
    seller_reg: str | None = None
    buyer_reg: str | None = None
    seller_name: str | None = None
    buyer_name: str | None = None
    lines: list[InvoiceLine] = field(default_factory=list)
    totals: dict = field(default_factory=dict)   # sales_total, item_discount, vat, withholding, grand_total ...
    issues: list[dict] = field(default_factory=list)

    @property
    def period(self) -> tuple[int, int] | None:
        d = next((ln.period_from for ln in self.lines if ln.period_from), None)
        return (d.year, d.month) if d else None


def fix_word(w: str) -> str:
    """Logical reading of one visual-order token: NFKC folds presentation forms; Arabic words are char-reversed;
    digits/Latin stay as they are."""
    s = _BIDI.sub("", w)
    n = unicodedata.normalize("NFKC", s)
    if _LETTERS.search(n):
        # reverse BEFORE expanding presentation forms, so a lam-alef ligature (one glyph) keeps its letter order
        n = unicodedata.normalize("NFKC", s[::-1])
    return re.sub("[\ue000-\uf8ff]", "", n).translate(_PERSIAN)   # private-use glyphs (icons) carry no text


def fix_line(words: list[dict]) -> str:
    return " ".join(fix_word(w["text"]).translate(_AR_DIGITS) for w in sorted(words, key=lambda w: -w["x1"]))


def _dec(s: str | None) -> Decimal | None:
    if not s:
        return None
    t = s.replace(",", "").strip().strip("/")
    try:
        return Decimal(t)
    except Exception:
        return None


_NUM = re.compile(r"^/?[\d,]*\.?\d*$")


def _join_number(tokens: list[tuple[float, float, str]]) -> list[str]:
    """Numbers split across lines: '24,908.' + '/40000' -> '24,908.40000'. A fragment without a dot continues the
    previous number; a token with a dot starts a new one."""
    out: list[str] = []
    for _top, _x, t in sorted(tokens):
        t = t.translate(_AR_DIGITS)
        if not _NUM.match(t) or t in ("", "/"):
            continue
        t = t.lstrip("/")
        if out and "." not in t and out[-1].count(".") == 1 and not out[-1].endswith(("%",)) and len(out[-1].split(".")[1]) < 5:
            out[-1] += t
        else:
            out.append(t)
    return out


def classify_description(desc: str) -> dict:
    n = normalize_text(desc)
    packages = sorted({int(x) for x in re.findall(r"\d+", n) if int(x) in PACKAGES})
    return {
        "kind": "excess" if "اضافي" in n else ("rent" if "تاجير" in n else "other"),
        "packages": packages, "color": "الوان" in n, "a3": "a3" in n or "زيروكس" in n, "printers": "طابعات" in n or "طابعه" in n}


def _role(header_words: list[str]) -> str | None:
    n = normalize_text(" ".join(header_words))
    if "سعر" in n and "الوحده" in n:
        return "unit_price"
    if "الكميه" in n:
        return "qty"
    if "مبيعات" in n and "اجمالي" in n:
        return "sales_total"
    if "صافي" in n:
        return "net_total"
    if "قيمه" in n and "الضريبه" in n and "فرق" not in n:
        return "tax_value"
    if "المجموع" in n:
        return "total"
    if "الوصف" in n:
        return "description"
    return None


def parse_invoice(content: bytes) -> Invoice:
    import pdfplumber
    inv = Invoice()
    try:
        pdf_cm = pdfplumber.open(io.BytesIO(content))
    except Exception as exc:  # unreadable / not a PDF
        raise UnrecognisedInvoice(f"Not a readable PDF: {exc.__class__.__name__}") from exc
    with pdf_cm as pdf:
        if not pdf.pages:
            raise UnrecognisedInvoice("Empty PDF")
        first = pdf.pages[0]
        words = first.extract_words()
        if not words or "eInvoicing" not in (first.extract_text() or ""):
            raise UnrecognisedInvoice("Not an ETA e-invoice (no 'eInvoicing' header / text layer)")
        _header(inv, first, words)
        n, roles = 0, []
        for pi, page in enumerate(pdf.pages, 1):
            roles = _page_roles(page) or roles  # later pages repeat the same column layout
            if roles:
                n = _items(inv, page, pi, roles, n)
        _totals(inv, pdf)
    if not inv.lines:
        raise UnrecognisedInvoice("No invoice lines found")
    _check(inv)
    return inv


def _header(inv: Invoice, page, words) -> None:
    lines: dict[int, list[dict]] = {}
    for w in words:
        lines.setdefault(round(w["top"] / 3), []).append(w)
    keys = sorted(lines)
    texts = [fix_line(lines[k]) for k in keys]
    mid = page.width / 2
    for i, t in enumerate(texts):
        if m := re.search(r"\b[0-9A-Z]{20,32}\b", t):
            inv.electronic_id = inv.electronic_id or m.group(0)
        n = normalize_text(t)
        nxt = texts[i + 1] if i + 1 < len(texts) else ""
        if "الداخلي" in n and not inv.internal_no:
            inv.internal_no = re.sub(r"\D", "", nxt) or re.sub(r"\D", "", t) or None
        if "تاريخ" in n and "الاصدار" in n and not inv.issued_on:
            # the date is stored visually reversed ("9 8/ 2026/" for 9/8/2026): day month/ year/
            if m := (re.search(r"(\d{1,2})\s+(\d{1,2})\s*/\s*(20\d{2})\s*/", t + " " + nxt)
                     or re.search(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(20\d{2})", t + " " + nxt)):
                try:
                    inv.issued_on = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                except ValueError:
                    pass
        if "حاله الفاتوره" in n:
            inv.status = (nxt or "").strip() or None
        if "رقم التسجيل" in n:
            val = re.sub(r"\D", "", nxt)
            if len(val) >= 9:
                if "للبا" in n:
                    inv.seller_reg = inv.seller_reg or val
                else:
                    inv.buyer_reg = inv.buyer_reg or val
    # party names: the line under the "name / name" header, split by page half (right = seller, left = buyer)
    for idx, k in enumerate(keys):
        ws = lines[k]
        if len(ws) == 2 and all(fix_word(w["text"]).endswith("سم") and len(fix_word(w["text"])) <= 6 for w in ws) and idx + 1 < len(keys):
            below = lines[keys[idx + 1]]
            right = [w for w in below if (w["x0"] + w["x1"]) / 2 > mid]
            left = [w for w in below if (w["x0"] + w["x1"]) / 2 <= mid]
            inv.seller_name = fix_line(right) or None
            inv.buyer_name = fix_line(left) or None
            break


def _page_roles(page) -> list[tuple[float, float, str]]:
    for table in page.find_tables():
        hdr = next((r for r in table.rows if sum(1 for c in r.cells if c) >= 10), None)
        if hdr is None:
            continue
        roles = []
        for c in hdr.cells:
            if not c:
                continue
            box = (max(c[0], 0), max(c[1], 0), min(c[2], page.width), min(c[3], page.height))
            ws = page.crop(box).extract_words()
            role = _role([fix_word(w["text"]).translate(_AR_DIGITS) for w in ws])
            if role:
                roles.append((box[0], box[2], role))
        if {r[2] for r in roles} >= {"unit_price", "qty", "description", "sales_total"}:
            return roles
    return []


def _items(inv: Invoice, page, pi: int, roles: list, n: int) -> int:
    """Item bands are located by the 'EGS' code word of each item (not by table rows: an item that straddles a page
    break or has no ruling would be missed)."""
    words = page.extract_words()
    egs = sorted(w["top"] for w in words if w["text"] == "EGS")
    if not egs:
        return n
    left, right = min(r[0] for r in roles), max(r[1] for r in roles)
    # the totals block (rows labelled with the currency) ends the last item's band
    below = [w for w in words if w["top"] > egs[-1] + 40]
    limit = page.height
    lines: dict[int, list[dict]] = {}
    for w in below:
        lines.setdefault(round(w["top"] / 3), []).append(w)
    for k in sorted(lines):
        t = fix_line(lines[k])
        if "م.ج" in t.replace(" ", "") or "ج.م" in t.replace(" ", ""):
            limit = min(w["top"] for w in lines[k]) - 2
            break
    for idx, top in enumerate(egs):
        start = top - 26  # a 3-line description starts up to ~25pt above its 'EGS' code
        end = (egs[idx + 1] - 26) if idx + 1 < len(egs) else limit
        cols: dict[str, list[dict]] = {}
        for w in words:
            if not (start <= w["top"] < end):
                continue
            xc = (w["x0"] + w["x1"]) / 2
            if not (left <= xc <= right):
                continue
            role = next((r for a, b, r in roles if a <= xc < b), None)
            if role:
                cols.setdefault(role, []).append(w)
        n += 1
        lns: dict[int, list[dict]] = {}
        for w in cols.get("description", []):
            lns.setdefault(round(w["top"] / 3), []).append(w)
        desc_lines = []
        for _k, lw in sorted(lns.items()):
            txt = fix_line(lw)
            nt = normalize_text(txt)
            if "قيمه الضريبه" in nt or "نوع الضريبه" in nt or "قيمه" == nt.split(" ")[0] and "الضريبه" in nt:
                break
            desc_lines.append(txt)
        desc = re.sub(r"\s*قيمة\s*$", "", " ".join(desc_lines)).strip()

        def tok(role):
            return [(w["top"], w["x0"], w["text"]) for w in cols.get(role, [])]
        qty, unit, sales = _first(tok("qty")), _first(tok("unit_price")), _first(tok("sales_total"))
        net, total = _first(tok("net_total")), _first(tok("total"))
        rates = [(w["top"], w["text"].translate(_AR_DIGITS)) for w in cols.get("sales_total", []) if "%" in w["text"] and re.search(r"\d", w["text"])]
        taxv = [(w["top"], w["text"].translate(_AR_DIGITS)) for w in cols.get("tax_value", []) if re.fullmatch(r"[\d,]+\.\d{3,5}", w["text"].translate(_AR_DIGITS))]
        vat = wht = vr = wr = None
        for rtop, rate in sorted(rates):
            value = min(taxv, key=lambda t: abs(t[0] - rtop), default=None)
            val = _dec(value[1]) if value and abs(value[0] - rtop) < 6 else None
            if vr is None:
                vat, vr = val, _dec(rate.replace("%", ""))
            else:
                wht, wr = val, _dec(rate.replace("%", ""))
        d_from = d_to = None
        dates = [date(int(a), int(b), int(c)) for a, b, c in re.findall(r"(20\d{2})-(\d{1,2})-(\d{1,2})", desc)]
        if dates:
            d_from, d_to = min(dates), max(dates)
        elif m := re.search(r"(20\d{2})-(\d{1,2})", desc):  # day tokens can be split by the PDF; the month is still stated
            d_from = date(int(m.group(1)), int(m.group(2)), 1)
        cl = classify_description(desc)
        inv.lines.append(InvoiceLine(n, pi, desc, cl["kind"], cl["packages"], cl["color"], cl["a3"], cl["printers"], _dec(qty), _dec(unit),
                                     _dec(sales), _dec(net), vat, vr, wht, wr, _dec(total), d_from, d_to))
        if vat is None:
            inv.lines[-1].flags.append("tax_detail_not_read")
    return n


def _first(tokens) -> str | None:
    nums = _join_number(tokens)
    return nums[0] if nums else None


def _totals(inv: Invoice, pdf) -> None:
    for page in pdf.pages:
        for t in page.find_tables():
            for row in t.rows:
                cells = [c for c in row.cells if c]
                if len(cells) < 2:
                    continue
                texts = [page.crop(c).extract_text() or "" for c in cells]
                joined = " ".join(" ".join(fix_word(w) for w in tx.replace("\n", " ").split()[::-1]) for tx in texts[1:])
                val = _join_number([(0, 0, w) for w in texts[0].translate(_AR_DIGITS).replace("،", ",").split()])
                if not val:
                    continue
                n = normalize_text(joined)
                key = None
                if "اجمالي المبيعات" in n:
                    key = "sales_total"
                elif "خصم الاصناف" in n:
                    key = "item_discount"
                elif "اجمالي الخصم" in n:
                    key = "total_discount"
                elif "القيمه المضافه" in n:
                    key = "vat"
                elif "تحت حساب" in n:
                    key = "withholding"
                elif "خصم اضافي" in n:
                    key = "extra_discount"
                elif "المبلغ الاجمالي" in n:
                    key = "grand_total"
                if key and key not in inv.totals:
                    inv.totals[key] = _dec(val[0].replace(",", ""))


def _check(inv: Invoice) -> None:
    tol = Decimal("0.01")
    for ln in inv.lines:
        if ln.qty is not None and ln.unit_price is not None and ln.sales_total is not None and abs(ln.qty * ln.unit_price - ln.sales_total) > tol:
            ln.flags.append("line_arithmetic_mismatch")
        if None in (ln.qty, ln.unit_price, ln.sales_total):
            ln.flags.append("line_incomplete")
        if ln.kind == "other":
            ln.flags.append("line_kind_unrecognised")
    if not inv.totals:
        inv.issues.append({"code": "invoice_totals_not_read", "severity": "warning", "message": "Invoice totals block could not be read"})
