# Financial Custody — analysis & reporting module (proposal, no code yet)

**Supersedes** §3/§6 of `CUSTODY_DISCOVERY.md` (transaction/workflow model is *parked*, not deleted: built only if requested).
Purpose: UPLOAD EXCEL → VALIDATE → ANALYZE → KPI + TABLES + CHARTS → EXECUTIVE REPORT. Source data is preserved; nothing is invented.

## 1. Pipeline (reuses the existing import pipeline)
1. **Detect layout** (layout profiles in `app/modules/custody_analysis/profiles/`): `pivot_custodian_by_category` (F1), `wide_branch_by_category` (F2), `gl_settlement_lines` (F3), `advance_register` (F4). Unknown layout → report "not recognised", never guess.
2. **Stage** raw rows immutably; **map** to the canonical analytical fact; **validate** (see §3).
3. **Compute** metrics (deterministic SQL/pandas, every figure traceable to source rows).
4. **Report**: dashboard + Excel + PDF (PPT later). Executive summary is generated from computed facts (template); optional AI wording may rephrase but cannot add numbers.

## 2. Canonical analytical fact `custody_expense_fact`
`dataset_id, period (month; date only if source has it), scope {head_office|branch|unspecified}, branch_id (nullable; resolved via entity_alias, never generated), branch_source_text, holder_source_text (admin-only), expense_category_source (original), account_no_source, cost_center_source, amount, direction, source_ref (file/sheet/row/cell), layout, flags`.
Original category names stay as-is; a display label table (EN↔AR) and an optional *reporting group* mapping are separate, approved by the user, never silently merged (e.g. `Public Relation`/`Public Relations`, `Training & Hosting`/`Hosting & Training`, `fuel & vehicles`/`Fuel & Vehicles Exp` are flagged as possible variants).
Advance-register data (F4) goes to a small `custody_advance_fact` (issue date, amount, branch, purpose text, settlement date text→date, raw kept) used **only for analysis** (issued vs settled, ageing, lag) — no workflow state.

## 3. Validation (flag, never fix)
Layout recognised; month recognised; control totals — computed vs the file's own Total/subtotal rows (difference shown); row total ≠ Σ components; hard-coded totals; stray helper cells; duplicate/ambiguous branch names; branch not in branch master; month spelling variants; negative amounts and reclass lines; empty-month sheets; categories present in one month only; column sets that change between months; custodian-name variants.

## 4. What each reference file supports

| Analysis | F1 HO pivot | F2 branch wide | F3 GL settlements | F4 advance register |
|---|---|---|---|---|
| Total expenditure for period | Yes (HO only) | Yes (branches only) | Yes (temporary-custody closings only) | No expenditure — advances issued only |
| By category + % share | Yes | Yes | Yes (original class; 39 accounts→26 classes) | No (purpose is free text) |
| Monthly trend, MoM change | Yes | Yes | Yes (Jan–Jul) | Issued/settled by month |
| Head Office vs branches | No (HO only) — combine with F2 *only if the user declares both belong to the same population* | idem | Yes (HO = cost-centre "Head Office") | Yes (branch column; groups stay groups) |
| By branch × category | No | Yes | Yes | No |
| Top branches / categories | Categories only | Both | Both | Branch by advances issued |
| Branch-to-branch comparison | No | Yes | Yes | Partial |
| Unusual patterns | Yes (by holder/category/month) | Yes | Yes | Ageing/lag outliers |
| Custodian view | Yes (admin-only) | No | Yes (from description text, admin-only) | Yes (admin-only) |

Multiple files are **never added together automatically**: the report states each file's scope; combining requires an explicit "same population/period" choice, because F3 and F1+F2 demonstrably do not nest.

## 5. Analysis outputs
**KPI cards:** total expenditure; # branches with spend; HO share %; top category and its %; top branch and its %; average monthly spend; latest month vs previous (Δ, Δ%); highest/lowest month; # flagged anomalies; data-coverage score.
**Tables:** category × month (+ % of total, rank); branch × category matrix; branch ranking (total, share, cumulative %, rank change vs previous month); HO vs branches by month and category; MoM variance (absolute/%) per category and per branch; unusual-items list (rule that fired, value, baseline); control-total reconciliation; data-quality log; "not supported by this file" list.
**Charts:** monthly trend (line/columns with MoM labels); category share (sorted bars, not pie when >6); HO vs branches stacked by month; Top-N branches (bars); category × month heatmap; branch × category heatmap; variance waterfall (month → month by category); Pareto (cumulative share); box/strip of branch spend distribution (comparison).
**Unusual-pattern rules (deterministic, thresholds configurable; defaults to be confirmed):** MoM change beyond ±X% and ±Y EGP; value above Q3+1.5·IQR of its own category across branches or of the branch's own months; single line > Z% of its category; branch with zero then spike / new / disappeared; category appearing once; negative or reclass lines; round-number recurring amounts; month total vs trailing average. With ≤8 months, statistical tests are shown as "indicative" and the rule text is displayed.
**Executive summary:** 6–10 sentences, each bound to a metric id (hover shows source cells); sections: headline spend, trend, mix, HO vs branches, concentration (top-N share), changes needing attention, data caveats.

## 6. Dashboard structure
1 Executive summary (KPI cards + 5 key findings + caveats) · 2 Spend & trend · 3 Categories · 4 Head Office vs branches · 5 Branches (ranking, matrix, compare 2–5 branches) · 6 Variances & unusual items · 7 Detailed tables (export) · 8 Data coverage & quality (what is/isn't supported, control totals) · optional 9 Advances (issued, settled, ageing) for F4. Filters: period range, scope, branch, category. Personal data (holder names) hidden unless role = admin.

## 7. Implementation notes
New module package `custody_analysis` (module.yaml / schema / kpis / rules / profiles), reusing registry, staging, entity resolution, exceptions, RBAC and the report/export layer; no new transaction tables beyond the two fact tables. Tests use synthetic files per layout; real files never committed.
