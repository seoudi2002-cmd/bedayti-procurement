# Procurement register analytics

Analysis only (no purchasing workflow): **upload → load/validate → analyze → dashboard → executive report (PDF / Excel)**. It sits on the platform's generic analysis API as module
`procurement`; loading **reuses the existing register loaders** (suppliers, requisitions, purchase orders [register profile], finance handover, branch master — with their
entity resolution, review queue and exceptions); this module only analyses what they hold. Source files are staged untouched; nothing is invented: a PO with no stated total is a PO
but never "0 spend"; cancelled POs are kept, flagged and shown separately.

## Upload
`POST /api/analysis/procurement/datasets` with the register workbook (any of the sheets: suppliers, requisitions, purchase orders, finance handover) or the branch master workbook.
Sheets are recognised by title and loaded in dependency order (branches → suppliers → requisitions → POs → finance). Re-uploading a cumulative export is an idempotent upsert; the same file again is a 409.
Registers are reference data and are not deleted from the dashboard (correct them by uploading the corrected file).

## What the report shows (one item, `all`; filters: month, supplier, department)
* **Summary:** PO count (priced / unpriced), PO value (Σ stated totals), average PO, suppliers, cancelled POs (flagged), requisitions and how many led to a PO, finance-handover memos (PO memos vs service memos),
  handed / remaining per the PO register.
* **Monthly:** POs and value by PO-date month with change vs the previous month; requisitions and finance memos by their own month; the latest month is flagged incomplete when the data ends before it does.
* **Suppliers:** value, share, cumulative share, average; top-N concentration; supplier category.
* **Categories:** PO category (source wording).
* **Departments and flow:** requisitions by requesting department (urgent, converted to a PO), requisition status and priority, PO status — all as written in the registers.
* **Finance and lead times:** requisition→PO and PO→finance-memo days (median, p90, negative, above the limit); per-PO handover coverage (none / partial / full / above the PO total / no total); memos by category.
* **Quality:** branch attribution of POs (confirmed only from explicit evidence; otherwise «Unallocated / needs review»), what each file loaded (rows, loaded, held), open exceptions by code with examples, thresholds used.

## Wording and limits (stated in every report)
«Handed to Finance» / «completed and paid» are the registers' own words, not bank-confirmed payments. No status-based exclusion rules are defined yet. Not available: bank payments and dates (no payment ledger),
items/quantities/unit prices (register is header level), savings and quotation comparison (no quotation data).

## Settings (no code change)
`procurement.thresholds`: `top_n`, `concentration_top_n`, `mom_change_pct`, `long_lead_days`, `reconcile_tolerance` — initial values awaiting confirmation; each report lists the values used.
