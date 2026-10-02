"""Native (text-layer) PDFs: tables straight from the PDF's text positions, no OCR."""
from app.core.extraction.table import Cell, RawTable, parse_ocr_number, role_of_header


def native_tables(pdf_path, page_no: int) -> list[RawTable]:
    import pdfplumber
    out: list[RawTable] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_no - 1]
        for tbl in page.extract_tables():
            if not tbl or len(tbl) < 2:
                continue
            header = [(c or "").replace("\n", " ") for c in tbl[0]]
            roles = [role_of_header(h) for h in header]
            if "description" not in roles:
                continue
            rt = RawTable(roles=roles, rows=[], page=page_no, source="pdf_native")
            for row in tbl[1:]:
                texts = [(c or "").replace("\n", " ").strip() for c in row]
                joined = " ".join(texts)
                if any(w in joined for w in ("الإجمالي", "الاجمالي", "Total", "TOTAL")) and not any(t.isdigit() for t in texts[:1]):
                    amount = next((t for t in reversed(texts) if parse_ocr_number(t) is not None and len(t) >= 2), None)
                    rt.stated_total_raw, rt.stated_total_conf = amount, 1.0
                    continue
                rt.rows.append([Cell(t, 1.0, page_no) for t in texts])
            out.append(rt)
    return out
