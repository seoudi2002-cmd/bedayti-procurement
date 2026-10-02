# Module catalog — one platform, shared master data, per-module transactions

Shared master data (all modules link to it): **branches/regions** (+Head Office, Regional Offices, Unallocated),
**employees**, **suppliers**, **departments/cost centres**, **categories** (source taxonomies kept separate until a
reporting taxonomy is agreed), **periods**. Each module owns its transaction tables and rules (`app/modules/<id>/`:
YAML config + `loader.py`), writes spend to the conformed `fact_cost` and quantities to `fact_usage`, and reports
problems to `data_exception`.

| # | Module | Status | Own tables | Needs from you |
|---|---|---|---|---|
| 1 | Procurement & POs | **built (register profile)**; line profile built, awaiting documents | `po_header`, `fact_po_line`, `fact_cost` | PO documents (lines), status → exclusion rules |
| 2 | Suppliers | **built** | `dim_supplier`, `supplier_contact` | status/blacklist policy |
| 3 | Requisitions | **built** | `requisition` | item/qty/estimate if documents provide them |
| 4 | Procurement Committee / Approvals | designed (document type exists) | `procurement_document(committee_approval)` + quotations/comparison tables | approval & quotation samples |
| 5 | Finance Handover | **built** | `finance_handover` | — |
| 6 | Payments | designed | `payment` (bank date, reference, amount, handover_id) | payment ledger |
| 7 | Branches & Regions | **built** | `dim_region`, `dim_branch`, `branch_contact` | codes, area m², regional offices |
| 8 | Employees | **built** (freshness-flagged) | `dim_employee` | as-of date, department/manager source |
| 9 | Printing / Copiers | designed | `dim_asset(copier)`, meter readings → `fact_usage`, rental invoices → `fact_cost` | machine register, meter reads, rental invoices |
| 10 | Paper consumption | designed | `fact_usage(reams)`, allocations per branch | distribution/allocation list (the `الفروع الجديدة` sheet?) |
| 11 | Rentals / Leases | designed | `lease_contract` (start/end/escalation/area), rent → `fact_cost` | lease register |
| 12 | Vehicles / Fleet | designed | `dim_asset(vehicle)`, fuel/maintenance/km → `fact_usage`/`fact_cost` | vehicle register, fuel & maintenance logs |
| 13 | Aramex / Logistics | designed | shipments → `fact_usage`, charges → `fact_cost` (service memos already carry the monthly totals) | shipment statements |
| 14 | **Financial Custody (العهد)** | designed below — core module | `custody_account`, `custody_movement`, derived balances/ageing | custody ledger sample + rules |
| 15 | Hotels / Accommodation | designed | `hotel_booking` (traveller→employee, nights, rate) → `fact_usage(room_nights)` + `fact_cost` | booking list/invoices |
| 16 | Asset Register & Maintenance | designed | `dim_asset` (+typed columns), `maintenance_event` | asset list, maintenance tickets |
| 17 | Savings & Cost Reduction | designed | `fact_savings`, quotation baselines | quotations / price comparison data |
| 18 | Management / Executive Reporting | planned | `kpi_value`, `insight`, `saved_report`, `report_run` | branding, report layouts |

Adding a module = copy `modules/_template`, write YAML (+ `loader.py`), add tables only if the shared facts do not fit.

## Financial Custody (العهد) — proposed design (not built; needs a sample ledger)
- `custody_account`: holder (`dim_employee`), branch (`dim_branch`), type (branch petty cash | employee advance | project …), opening date, limit, status, source reference.
- `custody_movement`: account, date, type (**issue / replenishment / expense / settlement / return / adjustment**), signed amount, document reference, category *(source text)*, description *(source)*, approver, batch lineage.
- **Balance** = running sum of movements per account (view; no stored balance to drift). **Ageing** = outstanding issued-but-unsettled amounts bucketed by age (0-30 / 31-60 / 61-90 / 90+); the matching rule (FIFO vs explicit settlement reference) must come from you.
- Exceptions: over limit, negative balance, expense without receipt/category, settlement older than policy, unreconciled account, holder not in HR file / left the company.
- KPIs: total open custody, number of open accounts, ageing profile, expenses by category/branch, settlement lag.
- Privacy: holder identity is personal data → admin-only; dashboards show branch/aggregate level.
Questions: custody types in use; who can hold; settlement policy and deadlines; limits; is each expense a separate document; how are replenishments approved; what is in the existing ledger (columns)?

## Architecture check (can it carry all of the above?)
Yes, with the work visible in the table. Known gaps, deliberately deferred: a shared declarative loader framework
(each loader is hand-written; extract once two more modules exist), KPI grouping by region/department and per-head/per-m²
normalisation (needs a join layer in the KPI engine), `procurement_*` table names are procurement-specific (a generic
`case`/`document` rename is cheap now and costly later — decision needed before module 4), real SSO (token auth is a stop-gap).
