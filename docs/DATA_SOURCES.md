# Reference data sources — analysis and DRAFT mapping

> **Status: DRAFT — not final.** Section 6 lists questions that must be answered before the mapping is frozen.
> This file contains **no names, phone numbers, e-mails or supplier names** (counts and row references only).
> The original workbooks were opened read-only and are not in the repository.

Analysed 2026-10-02: (A) procurement workbook, (B) branch workbook, (C) employee workbook.

## 1. What each file contains

### A. Procurement workbook — 4 sheets
| Sheet | Rows | Grain | Columns (business meaning) |
|---|---|---|---|
| سجل الموردين (supplier register) | 118 | 1 per supplier | `#`, register no., code `SUPnnn`, **supplier category** (27 values), services (41), contact person, phone, e-mail, address, commercial registry no., tax ID, notes |
| اشعارات الاحتياج (requisitions) | 60 | 1 per requisition | `م`, no. `n/2026`, request date, **requesting department** (3 values), need description (free text), priority (3), status (4), notes (empty) |
| اوامر الشراء (PO register) | 60 | **1 per PO — no lines** | `#`, PO no. `n/2026`, PO date, supplier name, supplier register no., supplier category, order description (free text), requisition no., **PO category** (7), `Column 14` (= PO issuance status), total amount, **order status** (7: execution/payment state), amount paid, remaining |
| استلامات المالية (finance handover) | 114 | 1 per memo sent to Finance | `#`, type (PO 61 / service 53), date sent to Finance, PO no., supplier name, supplier category, memo subject (free text), **purchase category** (13), memo amount |

### B. Branch workbook — 3 sheets
| Sheet | What it really is |
|---|---|
| فروع بدايتي | **The branch master**: 100 branches in 15 regions (governorates), region manager (merged cells), branch address, branch manager name, branch phone, manager phones, region-manager phones, branch e-mail. Region/region-manager cells are *merged* (must be filled down); 15 "subtotal" rows interleaved; one column hidden; a free-text column of notes. **No head-office row, no branch code, no area (m²)**. |
| الفروع الجديدة | Despite the name, **not a list of new branches**: 12 branches that already exist in the master, with columns `مبرد`/`كاتل` and quantities such as "3 ورق طباعة" / "3000 ورق دعايا" → looks like a **supply/allocation list** (paper, promotional paper, water coolers/kettles?). Unclear — see Q7. |
| Sheet1 | Scratch sheet: branch → governorate for 96 of the 100 branches (4 missing) plus stray personal contact notes. Not a source of truth. |

### C. Employee workbook — 1 sheet ("actives")
Row 1 is a control total (`HC` = 1,816, matches the data rows). Columns: code (unique, 1–8378 with gaps), full name, hire date (2021-06 → 2025-08), position (109 distinct), branch (115 distinct text values), governorate (27 values, **23 are `#N/A`** from a broken lookup). No department, manager, cost centre, national ID or salary.

## 2. Proposed mapping to the platform model

| Source | Target | Notes |
|---|---|---|
| B/فروع بدايتي | `dim_branch` (+ new `dim_region`) | one row per branch + one HQ row (HQ is missing from the file but is the delivery point of many POs and has 139 employees). Region from filled-down merged cells; branch manager and contacts as attributes (PII → restricted). Names seeded into `entity_alias` (variants like with/without spaces, hyphens). |
| C/Sheet3 | new `dim_employee` (code, name, hire_date, position, branch_id, governorate) | branch via alias resolution (see §3); headcount per branch computed from it → fills `dim_branch.headcount` for per-head normalisation (96 of 100 branches have employees). |
| A/سجل الموردين | `dim_supplier` (+ new columns: register_no, commercial_reg_no, contact, phone, email, address, status, payment_regime) | supplier *category* is its own taxonomy (27 spelling-inconsistent values) → `dim_category` with `kind = supplier`. |
| A/اشعارات الاحتياج | `procurement_case` + `procurement_document(requisition)` | number `n/2026` → (fiscal_year, number); department → `dim_cost_center`; priority/status as attributes; status drives case stage. |
| A/اوامر الشراء | `po_header` (**header-only**) + one `fact_cost` row per PO | new header columns needed: description, po_category, order_status, paid_amount (+ derived remaining), supplier register no. |
| A/استلامات المالية | `procurement_document(payment_request)` linked to PO when a PO no. exists; **service rows (no PO)** need a place of their own (see Q5) | 61 memos link to 50 distinct POs. |

## 3. Proposed connections (join keys) and how well they hold

| Link | Key | Result |
|---|---|---|
| PO → Supplier | supplier register no. (`#`) | 57/57 filled values exist in the register and the names agree; 3 POs (cancelled/pending) have no supplier. **Use the register no./`SUPnnn` code, not the name.** Caveat: register no. 105 occurs twice (rows with codes SUP105/SUP106). |
| PO → Requisition | requisition no. `n/2026` | 60/60 found. PO number ≠ requisition number in 3 rows (see Q3), so never assume they are equal. |
| Handover → PO | PO no. `n/yyyy` | 50 distinct POs; 4 belong to 2025 (the register only holds 2026 POs); 13 of the 2026 POs have no handover memo. |
| Handover → Supplier | **name only** (no ID) | 26/27 names match the register exactly after normalisation; 1 does not. |
| Employee → Branch | branch name text | 95 of 115 distinct values match the master after normalisation. The rest: head office (139 people), spelling variants, ~60 people recorded at "منطقة X" (regional offices), a few free-text multi-region entries. Needs an alias table (reviewed once). |
| Branch manager → Employee | manager name | 65 of 99 names match an HR record exactly (54 also in the same branch); 34 don't (spelling, or the manager is not in the HR file). |
| **PO → Branch** | — | **No link exists.** The PO register has no branch column; 22/60 descriptions mention branches in free text. |
| Requisition → Employee | — | No link (department only). |

## 4. Fields required by the PO loader

Current loader (Phase 1b) was designed for **line-level** exports and needs: PO no., PO date, branch, supplier, quantity, unit price (amount derived).
**The PO register cannot be loaded by it as-is** (no lines, no quantity/unit price, no branch). Proposed second import profile, "PO register" (header-level):

| Required | Optional / derived |
|---|---|
| PO no. (parsed into number + fiscal year from `n/yyyy`), PO date, supplier (register no. + name), requisition no. | total amount (empty for unpriced/cancelled POs → allowed, flagged), description, PO category, order status, issuance status, amount paid (remaining = total − paid, derived), supplier category (cross-check only) |

Loader changes this implies (not built yet — waiting for Q1/Q2): header-only mode; `n/yyyy` parsing; one `fact_cost` per PO with branch = unknown; extra header columns; date sanity check (reject dates far in the future); duplicate PO number detected → hold both rows for review instead of merging.

## 5. Data-quality findings (row numbers = Excel rows in the PO sheet unless stated)
- **Duplicate PO no. `36/2026`** (rows 28 and 37): different suppliers, different requisitions (`36/2026` and `34/2026`); `34/2026` is otherwise absent → row 37 is probably `34/2026`. Amount paid shows the same figure (≈ sum of both) on both rows → double counting if summed.
- **Number/requisition cross-over:** PO `29/2026` points at requisition `32/2026` and PO `32/2026` at `29/2026`; descriptions match the *requisition* cells → either POs were issued out of sequence or numbers were swapped.
- **Date typo:** PO `55/2026` dated 2062-09-06.
- **Paid > total** in 4 rows (`27/2026`, `36/2026` ×2, `49/2026`); `remaining` is blank in 41 of 60 rows and negative where overpaid.
- **Missing values:** 7 POs without amount (cancelled/pending/in-process), 3 without supplier, 3 requisitions without date, 15 branches without e-mail, 20 suppliers without tax ID, 25 without commercial registry no.
- **Handover vs register:** paid amount ≠ sum of memos for 3 POs (`41/2026`: memos total twice the PO value, two identical memos a month apart → possible duplicate; `43/2026`; `45/2026`). 1 PO-type memo has no PO no.; 1 service memo has one. 2 amounts are text with thousand separators.
- **Suppliers:** 2 pairs share a tax ID (one pair explained by a note: legal-entity change → superseded by #61); the tax-ID cell of one supplier holds the word "BLACKLISTED" and another is numeric; status information lives in free-text notes (10 suppliers "subject to advance-payment regime", 1 "do not deal again").
- **Three unrelated category schemes:** supplier category (27), PO category (7), handover purchase category (13).
- **Branch master:** phone numbers stored as numbers (leading 0 lost: `553413434`), some cells hold two phones; 4 branches missing from Sheet1; duplicate e-mail on one branch.
- **Employees:** 23 `#N/A` governorates; latest hire date 2025-08-18 (file may be stale); 1 duplicate full name.

## 6. Open questions (must be answered before the mapping is final)
1. **Line detail:** is there any source with quantity / unit price / items per PO (ERP export, PO PDFs, Excel)? Without it, item-level price variance, quote-vs-award savings and unit-cost KPIs are not possible.
2. **Branch attribution of spend:** how should a PO be attributed to branches (central/HQ, one branch, many branches)? Is there a distribution list per PO?
3. **Row corrections:** confirm PO `36/2026` (row 37 → `34/2026`?), the `29`/`32` cross-over, the 2062 date, the 4 paid-over-total rows and the possible duplicate memo for `41/2026`.
4. **"Amount paid":** cumulative per PO, including VAT, from Finance? Is there a payment ledger with bank value dates (the handover sheet has memo dates only)?
5. **Handover sheet meaning and service rows:** these are memos sent to Finance, not payments — confirm. The 53 service memos (≈ 3.6 M vs ≈ 10.6 M for POs) are recurring invoices (IT maintenance, courier, copier rental, beverage machines, safes maintenance…). Should they live in a "service contracts / recurring payments" register?
6. **Branch identity:** is there an official branch code? (The file has only a running number.) How should head office and regional offices ("منطقة X") be represented?
7. **الفروع الجديدة sheet:** what is it (allocation of paper/promotional paper and coolers/kettles to branches?) and does it belong to the paper module?
8. **Authoritative managers:** branch/region managers in the branch file vs HR file — which wins when they disagree (34 branch managers not found in HR)? Is the HR file dated (as-of)?
9. **Spend taxonomy:** which of the three category schemes should be the reporting standard, or do you want a new two-level taxonomy with mappings from all three?
10. **Departments / cost centres:** list of requesting departments (only 3 appear) and their owners.
11. **Supplier status:** formalise blacklist / advance-payment regime / superseded-by as fields? Confirm the second shared tax ID pair is legitimate.
12. **Personal data:** the files contain employee names, manager phones and e-mails. Confirm they may be stored in the cloud database (recommend: encrypted at rest, admin-only access, minimal fields; no salary/ID data requested).
