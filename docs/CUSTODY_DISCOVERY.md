# Financial Custody (العهد) — discovery, proposed model, decisions

Status: **proposal only — no code written.** Built from 4 workbooks + 1 email. This document contains structure, counts and
patterns only: no names, national IDs or amounts (real data is never committed).

## 1. Data profile

| # | File (role) | Sheets | Grain | Key columns |
|---|---|---|---|---|
| F1 | Head-Office expense analysis, Jan–Aug | 8 monthly + `Total` | pivot: custodian × expense account, **no dates/documents** | custodian name (free text), ~16 expense accounts, row total |
| F2 | Branch expense analysis, Jan–Aug | 8 monthly + `total` | wide: one row per branch × ~18 expense sub-columns | seq, branch name, month text, row total |
| F3 | Temporary-custody settlement journal, Jan–Jul | `Sheet1` (587 lines, 44 distinct JE numbers) + 2 pivots | **GL line** | Amount, account no., class 1 (expense class), class 2 (cost-centre code), branch (EN), description, JE number, month |
| F4 | Temporary-advance register 2026 (سلف مؤقتة) | 1 sheet, 140 advances + 7 monthly "اقفال" rows | **advance** | name, branch, advance date, amount, purpose, settlement text, status note |
| E1 | Email: request to open a temporary custody | — | request | branch → procurement/admin → finance; amount, purpose, cashier |

### F1/F2 (analysis workbooks)
* Reporting outputs, not source ledgers: no custody id, no dates, no document numbers; F1 month layouts change sheet to sheet (different column sets, accounts added/removed, `Row Labels` vs `Employees` vs `ACC.NAME` headers, custodian names written in 3+ styles).
* F1 mixes people and purpose in the key ("… سيارات ( … )" for one person on separate rows; the same person with 2–3 spellings across months).
* F2 February is a different layout (English branch names, 11 columns, no row numbers). Branch list grows 90 → 99 rows; some branches appear in only some months; Jun has a spelling variant of the month (`يونيه`) and rows with no sequence number.
* Stray/hard-coded cells: helper totals in column AN, hard-coded row totals that differ from the sum of their components (2 rows), subtotal rows that do not equal the sum of the visible rows in 5 of 7 monthly sheets (differences traced to the hard-coded rows and to totals placed in AN instead of V).
* The workbook month totals (`Total` sheets) are the only month-level control.

### F3 (settlement journal) — the closest thing to a custody ledger
* Every line is a **closing** entry: description pattern "اغلاق عهدة مؤقتة طرف <custodian> <purpose>" (579 lines; 4 "استكمال" top-up closings; 1 manual reclass `GL` entry with a negative amount, 2 lines).
* **JE number restarts every month** (e.g. the same JE code appears in 4–5 different months) → the real key is (month, JE no.).
* One JE = one custodian, 1..N expense lines (one per expense account; multi-branch trainings repeat the same amount per branch).
* Custodian name and purpose live **inside the description text**; custodian names there are shortened and sometimes have purpose text glued on (≈10 cases).
* class 2 is a cost-centre code; it maps 1:1 to a branch name except 3 codes with two spellings of the same branch and 1 branch name with two codes; 2 lines have no cost-centre code.
* 39 distinct account numbers collapse to 26 expense classes; `Meals`, `Training & Hosting` have 2–3 sub-accounts each; two parallel account families (51xxxxxx vs 61xxxxxx) carry the same class names (apparently branch vs head-office P&L — to be confirmed).
* The 3 "short-term receivable" accounts (12xxxxxx) and a penalty account (22601000) show that some closings are **not** operating expense (compensation to insurers, salary deductions, penalty fund).
* Total of the journal equals its own pivot (Sheet2/Sheet3) to the piaster — an internal control that can be reproduced.

### F4 (advance register)
* 140 advances, Jan 4 → Aug 11; monthly "اقفال شهر X" rows with SUM formulas for the advance column and a **hard-coded** second total in the settlement column (meaning not stated).
* Settlement is recorded only as **text** inside "عهد تحت التسوية": `تم التسوية بتاريخ d/m/yyyy` (122 rows); one value carries a typo (`…/20261`). 18 rows (all from 5 Jul on) have no settlement text = open. One row has a free-text note "تم استرجاع المبلغ كاملا" in the status column (full refund).
* The column named "الموقف" is empty for 139 rows; **there is no explicit status column**, no approval, no disbursement date, no document numbers, no custody type.
* Settlement lag (advance date → settlement date): median ≈ 25 days, max 118; 15 advances settled after more than 60 days; none negative.
* Purposes fall in clear families: branch petty cash "until a cashier is appointed", security/shutters installation, property tax, electricity arrears, court rent, training of branch groups, vehicle repair for executives, hospitality/fuel vouchers, inspection trips. "Branch" is a branch name, a **group** ("فروع البحيرة", "فروع قنا" …) or "المركز الرئيسي".
* Same custodian holds several advances at once or one after another (e.g. branch-cashier petty cash repeated each month).

### Cross-file reconciliation (F4 ↔ F3)
* Matching each F3 JE to an F4 advance by custodian name + amount: only **28 of 111 JEs** equal an advance amount exactly. The rest differ: spending below the advance (balance to return), above it (reimbursement), a JE covering several advances of one person, or one advance closed in several JEs. So the link must carry a **variance**, never be forced 1:1.
* Custodian names differ between F3 and F4 (short vs full name, extra words) → needs the employee master + alias approval, exactly like branches.
* F3 covers closings Jan–Jul only; F4 contains advances until Aug 11 (Aug closings absent from F3).
* Month totals of F1+F2 (expense analysis) are **not** a subset/superset of F3 (e.g. February: F3 closings exceed F1+F2). F1/F2 therefore cover a different population (probably permanent custodies + cash payments) — **unconfirmed**.

### E1 (email)
Shows the request channel: branch manager → procurement/admin (with finance contact copied) → "للافادة" forward. Contains an amount, purpose, cashier name, a personal ID number and a phone number (**personal data → admin-only fields**). The same branch already had a "until a cashier is appointed" advance earlier in the year, which the request itself says no longer exists.

## 2. What is NOT in the files (do not assume)
Permanent-custody (مستديمة) master/ceiling/opening balances; replenishment (تعزيز) entries; hotel custodies; request/approval dates and approvers; disbursement document (cheque/transfer) and date; settlement-form number; finance receipt/stamp date; documents attached; explicit status; any link from F1/F2 rows to a custody.

## 3. Proposed data model (shared masters reused: branch, employee, supplier-agnostic)
```
custody                 id, custody_no (from source if any; never generated silently), custody_type {permanent|temporary}, 
                        holder_employee_id (nullable) + holder_name_source, branch_id | branch_group_source,
                        purpose_text (original), purpose_category (reviewed), ceiling_amount (permanent only, NULL if unknown),
                        status (derived + override), source_ref (file/sheet/row)
custody_movement        id, custody_id, movement_type {request|approval|disbursement|replenishment|expense_settled|refund|top_up|
                        reclass|closure}, movement_date (nullable), amount, direction, document_no, source_ref
custody_settlement      id, custody_id, je_key (month+JE no.), settlement_date (from text, raw kept), settled_amount, 
                        submitted_to_finance_date, finance_receipt_date, copy_filed (bool) — all nullable until data exists
custody_expense_line    id, settlement_id, gl_account_no, expense_class (original), cost_center_code (original), branch_id, amount,
                        description_raw, month
custody_link            custody_id ↔ journal entry, method {amount_exact|name+date|manual}, confidence, review_status
custody_status_event    custody_id, status, at, source, by_user (history)
```
All "original" fields keep source text; corrections go through the existing override layer; unresolved names/branches/groups
create `data_exception`s (new codes below). Personal data (national ID, phone) is stored only in admin-only fields.

**Balance:** `open_balance = Σ disbursements + Σ top-ups − Σ settled expenses − Σ refunds` per custody (and per holder).
With the current files only `advance amount` and `settled amount` exist, so the balance is computed as
`advance − settled(F3 link)` and labelled **derived/needs review** until a disbursement/refund ledger is supplied.
Permanent custody balance = ceiling/opening − Σ settled expenses + Σ replenishments (needs opening balance and ceiling — missing).

**Status (derived, never invented):** requested · approved · disbursed (advance register row) · under_settlement (disbursed, no settlement date) ·
settled (settlement date present) · closed (settled and variance = 0 or refunded) · overdue (age rule — threshold TBD) · over/under-spent.
Statuses "requested/approved" need data that is not in the files yet.

**Temporary vs permanent:** temporary = one purpose, one closing JE ("اغلاق عهدة مؤقتة"). Permanent = recurring/no closing (hotels, vehicles) — no ledger received.

## 4. Exceptions detectable today (source untouched)
open advances aged > N days; settlement before advance date (none now); settlement-text typos; advances without settlement; one holder with several simultaneous open advances; JE variance vs advance (over/under); JE without matching advance; custodian name not in employee master; branch/cost-centre mismatch (3+1 cases); duplicate or missing cost-centre (2 lines); JE number reused across months (informational); manual reclass entries; negative amounts; hard-coded totals that differ from components in F2; subtotals ≠ row sums; month label variants; helper cells in AN; branch rows appearing/disappearing between months; branch group used as "branch".

## 5. KPIs / reports
Open custody balance (by holder, branch, type, age bucket); advances issued vs settled per month; settlement lag (median, p90, aged > 30/60/90); over/under-spend vs advance; spend by expense class × branch × month; share of custody spend in total admin spend; custodians with repeated/overlapping advances; "cashier-not-appointed" petty-cash advances per branch (a branch-coverage signal); top purposes; reconciliation status F3 ↔ F4; data-quality score per file.

## 6. Workflow (target; from the user's description)
request → approval → disbursement (finance) → purchases/expenses → collect invoices → settlement form + attachments → settlement approval → handed to finance → finance stamp/receipt → copy kept by Admin & Procurement. The platform tracks each step as a movement/event with date, document and user; today only *disbursement (advance date)* and *settlement date* exist in the files.

## 7. Decisions required (see chat for the numbered list)
