# Document extraction (PO line extractor)

Reads Word / native PDF / scanned PDF files and proposes structured lines. **Nothing is written to the PO tables until a person confirms.**

## Pipeline
1. `store_file` – file saved once (sha256); originals are never modified.
2. Per page: native text layer if present, else render at 300 dpi → Tesseract (ara+eng) with orientation/script detection and deskew.
3. `classify` – pages typed by weighted keywords (purchase_order, requisition, committee, finance memo, invoice, inspection…) and grouped into documents.
4. Headers – PO number, date, requisition, supplier, register no. (as-read `*_raw` kept).
5. Tables – scanned: ruling detection, rulings erased, header strip read for column roles, per-cell reading (digits-only for numbers), alternate readings accepted only if the arithmetic then holds. Native `.docx`/PDF tables share the same `RawTable → lines_from_table` validation.
6. Everything lands in `extracted_document` / `extracted_line` with confidence, page, bbox and flags.

## Flags (review catalogue)
`arithmetic_verified|mismatch|not_checkable`, `row_sequence_gap`, `table_total_verified|mismatch|unreadable`, `cell_alternate_reading`, `roles_inferred`, `unreadable_unit_price|line_total`, `no_line_table_found`, non-EGP currency, adjustment rows, `po_lines_total_differs_register`.

## Review workflow / API (`/api/extraction`, analyst role)
`POST /jobs` → `GET /documents/{id}` → `/link` to a PO → fix values via `/api/corrections` (override layer; original kept) → `/confirm` (purchase orders only; refuses incomplete lines; writes `fact_po_line` with lineage). Memos/invoices are cross-checks only (`/purchase-orders/{id}/cross-check`). Branch attribution is never invented: explicit text only, otherwise Unallocated and flagged.

## Findings from the first 5 files
- PO 32/2026 (12 lines) reads fully and sums to the stated total 677,950.
- PO 36/2026 prints the unit price in the total column; line 1 is flagged `arithmetic_mismatch` (source issue, not an OCR error).
- Word file: 64 memos, 188 lines. Payment-memo item names are unreliable; the PO is authoritative.
- Low-quality pages (OCR confidence 25–50) classify poorly and are flagged.

## Limits / deployment
~10–15 s per page; run as background job. Tesseract (ara, eng) and poppler are in the Docker image. Handwriting and heavily skewed pages need review. No external LLM/vision engine is used without explicit approval.
