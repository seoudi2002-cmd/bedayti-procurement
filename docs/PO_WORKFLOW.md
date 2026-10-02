# Purchase-order workflow & document model

Derived from one real, complete transaction (scans supplied privately; **not stored in this repo** — names,
tax IDs and signatures are deliberately omitted here). Tests use synthetic data.

## End-to-end chain (as observed)

| # | Document (`doc_type`) | Key data it carries | Links to |
|---|---|---|---|
| 1 | Requisition — إشعار الاحتياج (`requisition`) | fiscal year, number, date, requesting unit, item, qty, **estimated unit price**, usage pattern, reference to the previous purchase (PO no., committee date, invoice no., receipt date, total) | → case |
| 2 | Supplier quotations (`quotation`) ×N | supplier, date, item, unit price, validity, delivery time, payment terms, **VAT stated incl./excl.**, sometimes extra items or free goodies | → requisition |
| 3 | Price comparison (`price_comparison`) | per-supplier unit price × qty, subtotal, recommended supplier + reason | → quotations |
| 4 | Committee approval (`committee_approval`) | date, chosen supplier, price, total, attachment list, signatory roles | → requisition, comparison |
| 5 | Purchase order (`purchase_order`) | **fiscal-year-scoped number**, date, supplier record no., requisition no., requesting unit, purchase method, delivery site/period, payment terms, lines, total, 5 approval signatures; page 2 = standard terms (late penalty %/week with cap, ±qty tolerance, warranty) | → requisition, committee |
| 6 | Goods receipt (`goods_receipt`) | receipt date | → PO |
| 7 | Inspection & acceptance — نموذج فحص واستلام (`inspection_acceptance`) | date, **supplier invoice no.**, qty ordered / actual / invoiced, conformity, inspector | → PO, invoice |
| 8 | Supplier invoice (`supplier_invoice`) | e-invoice internal id + UUID, issue date, tax registrations, item, qty, unit price, discount, VAT, total, **PO reference field (blank in the sample)** | → PO |
| 9 | Payment / transfer request (`payment_request`) | request date, finance "received" stamp, supplier, amount, **due date = receipt + payment days**, tax-withholding note, attachment list | → PO, invoice |
| 10 | Bank transfer confirmation (`bank_transfer`) | bank reference, value date — **not in the sample** (only the request was) | → payment request |

Physical order in the PDF is the reverse of the lifecycle (payment on top, requisition at the bottom): never infer stage from page order.

## What this changed in the data model

- **PO is header + lines** (`po_header`, `fact_po_line`), not one flat row. Header: supplier, dates, requisition no., requesting unit (a *department*, so `dim_cost_center`), purchase method, delivery/payment terms, `terms` JSON for penalty/tolerance/warranty.
- **PO numbers restart each fiscal year** (the sample's previous PO was "No. 1"). Natural key = `(fiscal_year, po_number)`; `fiscal_year` is derived from the PO date if the file lacks it (`FISCAL_YEAR_START_MONTH`, FY named by its end year).
- **Delivery site may be head office, not a branch** → HQ is a `dim_branch` row (`branch_type = hq`).
- **VAT is explicit** (`vat_rate`, `vat_amount`): in the sample the quote says "excl. VAT", the PO says "incl. VAT", the invoice shows 0 VAT and the transfer letter says the item is exempt. `line_amount` = amount payable as stated on the PO; spend KPIs use it.
- **Document graph** ready for the rest of the chain: `procurement_case` (one per PO for now) ← `procurement_document` (typed, with `po_header_id`, optional `parent_id`/`relation`, JSON `attrs` for type-specific fields) ← `document_file` (scan/PDF). Allowed types and their lifecycle order live in `module.yaml` (`document_types`), so another module can define its own chain.

## Loader behaviour (Phase 1b)
- Upsert on `(fiscal_year, po_number, line_number)` → cumulative monthly re-exports are safe.
- A PO loads **all-or-nothing**; unknown/near-matching names are held and surfaced in `GET /api/aliases`, resolved with `POST /api/aliases/{id}/resolve` (`entity_id` or `create_new`), then `POST /api/imports/{id}/load` again.
- Policy per dimension in `module.yaml`: branches → review; suppliers/categories/items/cost centres → created on first sight. A *near* match (e.g. a typo) is always held, never auto-merged or auto-created.
- Each PO gets a case + `purchase_order` document; `GET /api/purchase-orders/{id}` shows documents on file, current stage and **missing required documents**.
- `POST /api/imports/{id}/rollback` removes what a batch wrote.

## Findings to turn into insight rules (Phase 4, `rules.yaml`)
Computable once the related documents are linked:
- **Savings baselines are ambiguous** — requisition estimate, last purchase price, average of other quotes, highest quote. Store all; report which baseline a savings figure uses. (Sample: awarded price was *above* the requisition estimate and *above* the previous purchase, but below every competing quote.)
- **Quote spread / competitiveness**: number of quotes, spread %, awarded rank.
- **Lead time & timeliness**: PO date → receipt vs promised delivery days; PO approval lag (last signature vs PO date).
- **Three-way match**: PO ↔ receipt/inspection ↔ invoice on qty and amount; **invoice without PO reference**.
- **Payment timeliness**: due date = receipt + payment days vs actual transfer.
- **Sequence violations**: receipt or invoice dated before approval (the sample's previous-purchase note suggests receipt preceded committee approval — worth verifying against the source).
- **Estimate accuracy**: requisition estimate vs awarded price per category.

## Not built yet
Quotation/comparison/invoice/payment loaders and file upload (`document_file`); data on these arrives as structured entry or
Excel exports first. Reading the scans automatically (Arabic print + handwriting + stamps) is possible later with AI-assisted
extraction, but only as *suggested fields a person confirms*.
