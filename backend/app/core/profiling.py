"""Structure profile of an unknown file (the first step for every new module: inspect before modelling).

Reports sheets/tables/pages, column types, fill rates, distinct counts, merged cells, hidden columns, formula-error
cells and date/number ranges. Cell VALUES are not reported unless `show_values` is set, so a profile can be shared
or stored without exposing personal or confidential data.
"""
import io
from collections import Counter
from datetime import date, datetime
from pathlib import Path


def _col_profile(name: str, values: list, show_values: bool) -> dict:
    filled = [v for v in values if v is not None and str(v).strip() != ""]
    types = Counter(type(v).__name__ for v in filled)
    out: dict = {"column": name, "filled": len(filled), "rows": len(values), "types": dict(types),
                 "distinct": len({str(v) for v in filled})}
    errors = [v for v in filled if isinstance(v, str) and v.strip().upper() in ("#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?")]
    if errors:
        out["formula_errors"] = len(errors)
    nums = [float(v) for v in filled if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if nums and len(nums) == len(filled):
        out["numeric"] = {"min": min(nums), "max": max(nums), "sum": round(sum(nums), 2)}
    dts = [v for v in filled if isinstance(v, (date, datetime))]
    if dts and len(dts) == len(filled):
        out["dates"] = {"min": min(dts).isoformat()[:10], "max": max(dts).isoformat()[:10]}
    texts = [str(v) for v in filled if isinstance(v, str)]
    if texts and len(texts) == len(filled):
        out["text_length"] = {"min": min(map(len, texts)), "max": max(map(len, texts))}
        if out["distinct"] <= 15:
            out["looks_categorical"] = True
            if show_values:
                out["values"] = dict(Counter(texts).most_common(15))
    if show_values and filled:
        out["examples"] = [str(v)[:40] for v in filled[:3]]
    return out


def profile_xlsx(content: bytes, show_values: bool = False) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), data_only=True)
    sheets = []
    for ws in wb:
        rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
        widest = max((sum(c is not None for c in r) for r in rows[:25]), default=0)
        hdr_idx = next((i for i, r in enumerate(rows[:25]) if sum(c is not None for c in r) >= max(2, 0.6 * widest)
                        and sum(isinstance(c, str) for c in r) >= 0.8 * sum(c is not None for c in r)), 0) if rows else 0
        headers = [str(c).replace("\n", " ").strip() if c is not None else f"column_{i + 1}" for i, c in enumerate(rows[hdr_idx])] if rows else []
        body = [r for r in rows[hdr_idx + 1:] if any(c is not None for c in r)]
        cols = [_col_profile(h, [r[i] if i < len(r) else None for r in body], show_values) for i, h in enumerate(headers)]
        sheets.append({
            "sheet": ws.title, "state": ws.sheet_state, "dimensions": ws.dimensions, "header_row": hdr_idx + 1,
            "data_rows": len(body), "merged_ranges": len(ws.merged_cells.ranges),
            "hidden_columns": [k for k, d in ws.column_dimensions.items() if d.hidden],
            "columns": [c for c in cols if c["filled"] or not c["column"].startswith("column_")],
            "title_rows_above_header": hdr_idx,
        })
    return {"kind": "xlsx", "sheets": sheets}


def profile_csv(content: bytes, filename: str, show_values: bool = False) -> dict:
    from app.core.ingestion.readers import read_table
    t = read_table(filename, content)
    cols = [_col_profile(h, [row.get(h) for _, row in t.rows], show_values) for h in t.headers]
    return {"kind": "csv", "header_row": t.header_row, "data_rows": len(t.rows), "columns": cols}


def profile_docx(content: bytes, show_values: bool = False) -> dict:
    import docx
    d = docx.Document(io.BytesIO(content))
    sigs = Counter(tuple((c.text or "").strip().replace("\n", " ")[:18] for c in t.rows[0].cells) for t in d.tables if t.rows)
    return {"kind": "docx", "paragraphs": len([p for p in d.paragraphs if p.text.strip()]), "tables": len(d.tables),
            "inline_images": len(d.inline_shapes),
            "table_header_signatures": [{"headers": list(k) if show_values else [f"col{i + 1}" for i in range(len(k))], "tables": v}
                                       for k, v in sigs.most_common(8)],
            "note": "Word files are read natively (no OCR): see /api/extraction"}


def profile_pdf(content: bytes, ocr_pages: int = 0) -> dict:
    import subprocess
    import tempfile
    from app.core.extraction import classify, pdfio
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "f.pdf"
        path.write_bytes(content)
        n = pdfio.page_count(path)
        native = [pdfio.has_text_layer(pdfio.native_text(path, p)) for p in range(1, n + 1)]
        out = {"kind": "pdf", "pages": n, "pages_with_text_layer": sum(native), "pages_scanned": n - sum(native),
               "needs_ocr": n - sum(native) > 0}
        if ocr_pages and out["needs_ocr"]:
            from app.core.extraction.ocr import default_engine, ocr_page_upright
            eng = default_engine()
            if eng.available():
                guesses = []
                for p in range(1, min(n, ocr_pages) + 1):
                    img = pdfio.render_page(path, p, Path(tmp))
                    pg = ocr_page_upright(eng, img, Path(tmp))
                    c = classify.classify_text(pg.text())
                    guesses.append({"page": p, "rotation": pg.rotation, "ocr_confidence": round(pg.mean_conf, 1),
                                    "type_guess": c.doc_type, "type_confidence": c.confidence})
                out["sampled_pages"] = guesses
        del subprocess
        return out


def profile_file(filename: str, content: bytes, show_values: bool = False, ocr_pages: int = 0) -> dict:
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return profile_xlsx(content, show_values)
    if ext in (".csv", ".txt"):
        return profile_csv(content, filename, show_values)
    if ext == ".docx":
        return profile_docx(content, show_values)
    if ext == ".pdf":
        return profile_pdf(content, ocr_pages)
    raise ValueError(f"Cannot profile '{ext}' files")
