# Schema additions (migration 0004) — additive only

No existing column is dropped, renamed or retyped; downgrade removes only what this migration adds (tested up → down → up,
`alembic check` clean on PostgreSQL 16).

## Correction layer
`data_override` — never overwrites a source value. One row per proposed correction: entity type/key (e.g. `po_header` `2026/55`),
field, **original value**, **corrected value**, **reason**, proposed by, proposed at, **status** (proposed → approved | rejected |
superseded | reverted), reviewed by/at/note, applied at. Rules:
- Only an **approved** correction changes the working value; it is re-applied automatically on every reload from source; reverting restores the source value and re-opens exceptions the correction had closed.
- The original is the true source value even after several corrections; the raw staged row is never touched.
- Whitelisted targets/fields only: `po_header` (date, total, supplier, branch, handover/remaining amounts, requisition no.), `po_line` (qty, price, amount, description, branch), `requisition` (date), `finance_handover` (amount, date, PO ref), `extracted_line` (qty, price, total, description) and `source_row` (a cell of a held/rejected staged row, e.g. the PO number of a conflicting row).
- Branch corrections set attribution to **confirmed / manual_override**, which later automatic attribution never overwrites.
- Single-user mode allows self-approval (`ALLOW_SELF_APPROVAL=true`); set it to `false` when more users exist to force four-eyes review.

## Document extraction
`extraction_job` (engine, versions, languages, status, summary) → `extracted_page` (text exactly as read, source native/ocr/docx,
rotation, mean confidence, rendered page image path, type guess) → `extracted_document` (logical document: type, pages,
header fields with value/**raw text**/confidence/page, flags, link to PO and how) → `extracted_line` (as-read `*_raw` values, parsed values,
per-field confidence, flags, bbox on the page, price basis, line-level branch evidence, link to the PO line once confirmed).
`document_file` gains `source_kind`; `procurement_document` gains `page_from/page_to` so every document on file points at its pages.

## Lines linked to the PO and the file
`fact_po_line` gains `source_kind` (import | document_extraction), `extracted_line_id` (→ the line as read → the page of the original),
`price_basis` (incl_vat | excl_vat | NULL), and branch attribution columns (method/status/source text, same audit trail as the header).
`po_header.lines_total` keeps the sum of confirmed lines **next to** the register's stated `total_amount` (a difference is an exception, neither value overwrites the other).

## Branch allocation of a line
`po_line_allocation` (line, branch, quantity/amount, **source**: explicit_text | allocation_file | receipt_form | manual, source reference, **status**: proposed | confirmed | rejected, decided by). Nothing writes to it automatically yet: allocations will only come from an explicit allocation source or a person's decision.
