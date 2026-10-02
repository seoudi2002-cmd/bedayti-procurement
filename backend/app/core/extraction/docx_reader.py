"""Native Word documents → memos with line tables (no OCR needed: text and table cells are exact).

A .docx may hold many memos back to back (the company keeps one running file). A memo starts at a paragraph
"التاريخ : dd / mm / yyyy" that is followed by the addressee/subject; its line table(s) are those until the next memo.
"""
import re
from dataclasses import dataclass, field

from app.core.cleaning.normalizers import normalize_text
from app.core.extraction.headers import TextLine
from app.core.extraction.table import Cell, RawTable, parse_ocr_number, role_of_header


@dataclass
class DocxMemo:
    seq: int
    lines: list[TextLine]
    tables: list[RawTable] = field(default_factory=list)
    text: str = ""


def _cell_texts(row) -> list[str]:
    """Cell texts with merged cells reported once (python-docx repeats the same cell object across a merge)."""
    seen, out = set(), []
    for c in row.cells:
        key = id(c._tc)
        out.append("" if key in seen else c.text.strip())
        seen.add(key)
    return out


def _cell_spans(row) -> list[int]:
    """For each column, the index of the first column of the (possibly merged) cell covering it."""
    first: dict[int, int] = {}
    spans = []
    for i, c in enumerate(row.cells):
        first.setdefault(id(c._tc), i)
        spans.append(first[id(c._tc)])
    return spans


def raw_table_from_docx(table, seq: int) -> RawTable | None:
    if len(table.rows) < 2:
        return None
    header = [t.replace("\n", " ") for t in _cell_texts(table.rows[0])]
    roles = [role_of_header(h) for h in header]
    if not (("description" in roles) and ("qty" in roles or "unit_price" in roles or "total" in roles)):
        return None  # e.g. a signature block
    out = RawTable(roles=roles, rows=[], page=seq, source="docx")
    basis_text = " ".join(header)
    for row in table.rows[1:]:
        texts = [t.replace("\n", " ") for t in _cell_texts(row)]
        spans = _cell_spans(row)
        notes: dict[int, str] = {}
        desc_i, qty_i = (roles.index("description") if "description" in roles else None), (roles.index("qty") if "qty" in roles else None)
        # a text cell merged across the quantity and description columns belongs to the description
        if desc_i is not None and qty_i is not None and spans[desc_i] == spans[qty_i] != desc_i and not texts[desc_i] \
                and texts[qty_i] and parse_ocr_number(texts[qty_i]) is None:
            texts[desc_i], texts[qty_i] = texts[qty_i], ""
            notes[desc_i] = "merged_cell_text_moved_from_quantity_column"
        first = normalize_text(" ".join(t for t in texts if t))
        if first.startswith(("الاجمالي", "اجمالي", "total", "المجموع")) or "الاجمالي" in normalize_text(texts[0] if texts else ""):
            amount = next((t for t in reversed(texts) if parse_ocr_number(t) is not None and len(re.sub(r"\D", "", t)) >= 2), None)
            if amount is not None and ("غير" not in normalize_text(" ".join(texts)) or out.stated_total_raw is None):
                if "غير شامل" not in normalize_text(" ".join(texts)):
                    out.stated_total_raw, out.stated_total_conf = amount, 1.0
                else:
                    out.notes.append(f"subtotal_excl_vat={amount}")
            continue
        out.rows.append([Cell(t, 1.0, seq, None, notes.get(i)) for i, t in enumerate(texts)])
    out.price_basis_text = "غير شامل الضريبة" if "غير شامل" in normalize_text(basis_text) else (
        "شامل الضريبة" if "شامل" in normalize_text(basis_text) else None)
    return out


_MEMO_START = re.compile(r"^\s*التاريخ\s*[:：]")


def read_docx(path) -> list[DocxMemo]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    d = docx.Document(str(path))
    memos: list[DocxMemo] = []
    cur: DocxMemo | None = None
    for child in d.element.body.iterchildren():
        if child.tag.endswith("}p"):
            text = Paragraph(child, d).text.strip()
            if not text:
                continue
            if _MEMO_START.match(text):
                cur = DocxMemo(seq=len(memos) + 1, lines=[])
                memos.append(cur)
            if cur is not None:
                cur.lines.append(TextLine(text, 1.0, cur.seq))
        elif child.tag.endswith("}tbl") and cur is not None:
            rt = raw_table_from_docx(Table(child, d), cur.seq)
            if rt is not None:
                cur.tables.append(rt)
    for m in memos:
        m.text = "\n".join(l.text for l in m.lines)
    return memos
