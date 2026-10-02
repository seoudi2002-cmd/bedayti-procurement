"""Page → document type, from keywords in the (OCR'd or native) text.

Deliberately simple and explainable: each type has weighted keyword families (Arabic variants are folded by
normalize_text; OCR spelling damage is tolerated with short stems). The result carries a confidence and the
evidence; below a threshold the page is 'unknown' and goes to review instead of being forced into a type.
"""
import re
from dataclasses import dataclass

from app.core.cleaning.normalizers import normalize_text


@dataclass(frozen=True)
class Signal:
    pattern: str
    weight: float


# document types that start a new logical document vs. pages that continue the previous one
TYPES: dict[str, tuple[Signal, ...]] = {
    "purchase_order": (Signal(r"ام?ر\s*شر[اى][ءه]?\s*(?:رقم|رشم|رفم)", 4), Signal(r"مكان التسليم", 2), Signal(r"معدل التوريد", 2),
                       Signal(r"طريقه الشراء", 1.5), Signal(r"سجل موردين", 2), Signal(r"رقم الاشعار", 1.5), Signal(r"purchase order", 3)),
    "purchase_order_terms": (Signal(r"تابع\s*ام?ر\s*شر", 5), Signal(r"المهمات", 1.5), Signal(r"مهله التسليم", 2), Signal(r"غرامه التاخير", 2),
                             Signal(r"ضمان الاداء", 2), Signal(r"التفاصيل", 0.5)),
    "committee_approval": (Signal(r"لجنه المشتريات", 4), Signal(r"السادة\s*/?\s*لجنه", 2), Signal(r"الافضل من حيث الجوده والسعر", 3),
                           Signal(r"يرجي التكرم بالموافقه", 2)),
    "payment_request": (Signal(r"تحويل بنكي", 3), Signal(r"المدير المالي", 2), Signal(r"المدير المالى", 2), Signal(r"السداد 100", 1.5),
                        Signal(r"قيمه الضريبه المضافه", 0.5), Signal(r"يرجي التكرم بالموافقه علي اصدار", 2), Signal(r"تحويل بنكى", 3)),
    "requisition": (Signal(r"requisition", 4), Signal(r"اشعار الاحتياج", 1.5), Signal(r"الجهه الطالبه", 2), Signal(r"بيان المطلوب", 2)),
    "supplier_invoice": (Signal(r"\binvoice\b", 3), Signal(r"taxpayer", 3), Signal(r"registration number", 2), Signal(r"فاتوره", 2),
                         Signal(r"الرقم الالكتروني", 2), Signal(r"submission date", 3)),
    "inspection_acceptance": (Signal(r"نموذج\s*(?:فحص|فحصص)", 3), Signal(r"فحص واستلام", 4), Signal(r"فحص ومعاينه", 3)),
    "goods_receipt": (Signal(r"ايصال استلام", 4), Signal(r"نموذج\s*استلام", 3), Signal(r"استلمت انا", 2), Signal(r"اذن استلام", 3),
                      Signal(r"بيانات مستلم", 3), Signal(r"اقرار بالاستلام", 2)),
    "quotation": (Signal(r"\bquotation\b", 4), Signal(r"pricing offer", 4), Signal(r"عرض سعر", 3), Signal(r"عرض اسعار", 3),
                  Signal(r"كوتيشن", 3), Signal(r"صلاحيه العرض", 2), Signal(r"unit price", 1)),
    "price_comparison": (Signal(r"مقارنه عروض", 4), Signal(r"the recommendation", 3), Signal(r"recomm?endation is", 3), Signal(r"subtotal", 1),
                         Signal(r"vat (?:included|excluded)", 2)),
    "email": (Signal(r"\bfrom:", 2), Signal(r"\bsent:", 2), Signal(r"\bsubject:", 2), Signal(r"\battachments:", 1.5)),
    "tax_form": (Signal(r"مصلحه الضرائب", 3), Signal(r"دفعات مقدمه", 2), Signal(r"نموذج رقم\s*\(?\s*7", 3)),
    "commercial_registry": (Signal(r"مستخرج سجل تجاري", 4), Signal(r"مستخرج سجل تجارى", 4), Signal(r"السجل التجاري", 1), Signal(r"وزاره التموين", 2)),
    "site_inspection": (Signal(r"imp-?ans", 4), Signal(r"تعليق\s*:\s*\(?\s*تم عمل معاينه", 3), Signal(r"تم عمل معاينه", 3)),
}
# a page of these types opens a new document; everything else attaches to the previous one
STARTS_DOCUMENT = {"purchase_order", "committee_approval", "payment_request", "requisition", "supplier_invoice",
                   "inspection_acceptance", "goods_receipt", "quotation", "price_comparison", "email", "tax_form",
                   "commercial_registry", "site_inspection"}
MIN_SCORE = 3.0


@dataclass
class Classification:
    doc_type: str
    confidence: float
    evidence: list[str]


def classify_text(text: str) -> Classification:
    # lines that merely mention attachments ("مرفق أمر الشراء رقم (32)") must not make a page look like that document
    text = "\n".join(l for l in text.splitlines() if "مرفق" not in normalize_text(l))
    norm = normalize_text(text)
    if "مرفقات" in norm and len(norm.split()) < 110:  # an attachments/signature page belongs to the memo above it
        return Classification("unknown", 0.0, ["attachments_list"])
    scores: dict[str, tuple[float, list[str]]] = {}
    for doc_type, signals in TYPES.items():
        total, ev = 0.0, []
        for sig in signals:
            if re.search(sig.pattern, norm):
                total += sig.weight
                ev.append(sig.pattern)
        if total:
            scores[doc_type] = (total, ev)
    if not scores:
        return Classification("unknown", 0.0, [])
    best = max(scores, key=lambda t: scores[t][0])
    score, ev = scores[best]
    if score < MIN_SCORE:
        return Classification("unknown", round(score / (MIN_SCORE * 2), 3), ev)
    second = sorted((v[0] for k, v in scores.items() if k != best), reverse=True)[:1]
    margin = score - (second[0] if second else 0)
    conf = min(0.99, 0.45 + 0.08 * score + 0.05 * margin)
    return Classification(best, round(conf, 3), ev)


def group_pages(classes: list[Classification]) -> list[tuple[str, int, int]]:
    """Consecutive pages → logical documents [(doc_type, first_page_index, last_page_index)] (0-based, inclusive).
    A page that does not open a document (terms page, signature page, unreadable page) joins the previous one."""
    docs: list[list] = []
    for i, c in enumerate(classes):
        if c.doc_type in STARTS_DOCUMENT or not docs:
            docs.append([c.doc_type if c.doc_type != "purchase_order_terms" else "purchase_order", i, i])
        else:
            docs[-1][2] = i
    return [(t, a, b) for t, a, b in docs]
