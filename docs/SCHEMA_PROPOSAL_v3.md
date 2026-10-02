# Schema & mapping proposal (migration 0003) — additive only

**Nothing here drops, renames or rewrites existing data.** Migration `0003_reference_data_registers_exceptions` only
adds tables/columns and relaxes four NOT NULL constraints (listed in §4). Downgrade is provided and was tested
(up → down → up, `alembic check` shows no drift) on PostgreSQL 16. Original files are never modified, never
stored in git, and every raw row is kept untouched in `raw_row.payload`.

## 1. Principles applied (from the business owner's decisions)
| Decision | How it is implemented |
|---|---|
| Don't invent business data | No branch/supplier/cost-centre codes are generated (`code` is nullable and only ever filled from a source). Unknown suppliers/branches are held for review, not created. Missing values stay `NULL` and are labelled (`missing_fields`, `*_source`, exceptions). |
| Keep source text + method | Every derived value keeps its source: `description_source`, `po_date_source`, `branch_source_text` + `branch_attribution_method` + `attrs.branch_evidence`, `branch_match_method`, `*_category_source` … |
| Flag, don't silently fix | New `data_exception` table (cross-record issues) + `validation_issue` (row-level). Source rows are never edited. A person's decision (accepted/dismissed/resolved) survives re-imports. |
| "Amount paid" ≠ bank payment | PO-register column is stored as `finance_handover_amount_register`; handover memos in `finance_handover`; KPIs are named "Finance Handover Amount". A future payment ledger gets its own table. |
| Service memos are not POs | `finance_handover.memo_type` = `po` / `service`; service memos have no PO link and are never written to `po_header`. |
| Categories stay separate | `dim_supplier.category_source`, `po_header.po_category_source`, `finance_handover.purchase_category_source` (+ supplier category on PO/memo). No mapping/merge yet. |
| Both manager values kept | `branch_contact.branch_manager_name_source` (branch file) and `manager_employee_id` (HR match) + `manager_reconciliation_status`; disagreement → `data_exception`, nothing overwritten. |
| Employee file is "possibly stale" | `import_batch.warnings` + `employee_data_freshness` exception (latest hire date vs today); `/api/branches` returns the warning next to headcount. |
| Personal data admin-only | Contacts/managers/phones/e-mail in `branch_contact`, `supplier_contact`; HR in `dim_employee`; modules flagged `contains_personal_data` (admin-only endpoints, incl. their raw rows). Dashboards/KPIs only ever see ids and aggregates. |

## 2. New / changed tables
**Master data**
- `dim_region` (name) · `dim_department` (name, source) · `dim_employee` (employee_code, full_name, hire_date, position_source, branch_id, branch_source_text, branch_match_method, governorate_source, governorate_issue, department_id/cost_center_id/manager_employee_id = NULL + `missing_fields`).
- `dim_branch` + `system_key`, `source_seq`, `region_id`, `address`; `branch_type` ∈ branch | head_office | regional_office | unallocated. Two system rows: **Head Office**, **Unallocated / Branch Not Identified**.
- `branch_contact`, `supplier_contact` (personal data).
- `dim_supplier` + `register_no` (not unique: the source repeats one), `commercial_reg_no`, `address`, `category_source`, `services_source`, `notes_source`; `tax_id` kept as raw text.

**Procurement documents**
- `requisition` (fiscal_year, req_number, number_source, request_date NULL if missing/invalid, department, description/priority/status *source*, case_id).
- `po_header` + `number_source`, `po_date_source`, `supplier_name_source`, `supplier_register_no_source`, `branch_*` attribution columns, `requisition_id`, `granularity` (`header_only`|`lines`), `description_source`, `po_category_source`, `supplier_category_source`, `issuance_status_source`, `order_status_source`, `finance_handover_amount_register`, `remaining_register`.
- `finance_handover` (memo_no, memo_type, memo_type_source, sent_date, po_number_source, po_header_id, supplier_id + name source, subject/category *source*, amount).
- `procurement_document` + `ref_table`/`ref_id` (envelope → typed register row).

**Platform**
- `data_exception` (code, severity, status, entity_type/key, details JSON, decided_by/note; unique per code+entity).
- `import_batch` + `profile`, `column_map` (mapping used), `warnings`, `rows_skipped`.
- `entity_alias` + `method` (review | system_seed | policy_create).

## 3. Source → target mapping (sanitised; "Q" = still open, see §6)
**Branch workbook, sheet `فروع بدايتي` (primary master)** → `dim_region`, `dim_branch`, `branch_contact`
| Source column | Target | Notes |
|---|---|---|
| م | `dim_branch.source_seq` | only a running number; **no branch code exists (Q1)** |
| المنطقة (merged) | `dim_region.name` → `dim_branch.region_id` | filled down within the merged block |
| مدير المنطقة (merged) | `branch_contact.region_manager_name_source` | filled down, reset when a new region starts |
| اسم الفرع | `dim_branch.name_ar` | upsert key = normalised name |
| العنوان | `dim_branch.address` | |
| اسم مدير الفرع / phones / e-mail | `branch_contact.*` | personal data; phones stored as text exactly as in the cell (leading zeros that Excel dropped are **not** restored) |
| subtotal rows, stray rows | skipped (`rows_skipped`, kept in `raw_row`) | |
Other sheets (`الفروع الجديدة`, `Sheet1`) are **not loaded** (Q2).

**HR workbook** → `dim_employee`: كود→`employee_code` (key) · الاسم→`full_name` · تاريخ التعيين→`hire_date` · الوظيفة→`position_source` · الفرع→`branch_source_text` + resolved `branch_id` (exact | compact | alias | unresolved) · المحافظه→`governorate_source` (`#N/A` → NULL + `governorate_issue`). Department/cost centre/manager: not in source → NULL + `missing_fields`.

**Procurement workbook**
| Sheet | Target | Key / notes |
|---|---|---|
| سجل الموردين | `dim_supplier` + `supplier_contact` | key = كود المورد; register no. stored, not a key |
| اشعارات الاحتياج | `requisition` (+ `procurement_case`, `procurement_document`) | key = (FY, number) from `n/yyyy`; departments created from source values (`dim_department.source`) |
| اوامر الشراء (profile `register`) | `po_header` (header-only) + one `fact_cost` row when total and date are known | key = (FY, number); supplier by register no. (name = cross-check); requisition by stated number |
| استلامات المالية | `finance_handover` | key = memo `#`; PO link by `n/yyyy`; supplier by name via register (never created) |

## 4. Relaxed constraints (non-destructive)
`dim_branch.code`, `dim_supplier.code`, `dim_cost_center.code` → nullable (no invented codes) ·
`po_header.po_date`, `period`, `supplier_id`, `total_amount` → nullable (a missing/invalid value is `NULL`, never `0`/a guess).

## 5. Behaviour changes to be aware of
- Suppliers are no longer auto-created by the PO loader (`entity_policy.supplier = review`); unknown suppliers wait for the supplier register or a review decision.
- Spend KPIs read `fact_cost` (one cost source per PO: its lines if any, else the header total). `po_count` = all POs, `priced_po_count` = POs with a stated total; `avg_po_value` divides by the latter.
- Branch attribution is rule-based and conservative (see `core/attribution.py`, `core/procurement_attribution.py`): the PO's own words and its requisition decide; finance-memo subjects are used only when the PO says nothing, and otherwise raise `po_branch_evidence_conflict`. Plural wording ("5 فروع", "فروع الشركة", "100 فرع") never maps to one branch.
- The engine had a latent bug (`count(*)` KPIs without a column returned 1); fixed.

## 6. Open items needing your decision
1. **Branch code:** does an official code exist? (none is generated meanwhile.)
2. **`الفروع الجديدة` / `Sheet1`:** meaning of the sheet (allocation list?) before anything is loaded from it.
3. **Order statuses:** which PO/requisition statuses mean "cancelled/excluded from spend" (today nothing is excluded by status; the one cancelled PO has no amount).
4. **Resolving held rows:** how corrections are made — re-upload a corrected file, or add an in-platform override layer (original kept) — I recommend the override layer.
5. **Region offices:** `منطقة X` employee locations are unresolved until you decide to create regional-office rows (one click via `POST /api/aliases/{id}/resolve` with `branch_kind=regional_office`).
6. **Payment ledger** (bank dates) and **line-level PO documents** (see `docs/DOCUMENT_INTAKE.md`).
