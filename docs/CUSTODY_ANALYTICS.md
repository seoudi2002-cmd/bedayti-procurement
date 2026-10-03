# Financial Custody Analytics (implemented)

Analysis and reporting only — no request/approval/disbursement/settlement workflow. Flow:
**upload Excel → recognise layout → validate → analyze → KPIs + tables + charts + executive summary → PDF / Excel**.

## Layouts (read by `app/modules/custody_analysis/layouts.py`)
| Layout | Reference file | Scope | Notes |
|---|---|---|---|
| `gl_settlement_lines` | F3 – temporary-custody settlement journal | temporary custody (Head Office + branches via cost-centre/branch) | year read from the file's own title (or supplied at upload) |
| `monthly_branch_expense` | F2 – branch expense analysis | branches | Arabic wide sheets (group + sub-item headers) and English pivot sheets |
| `monthly_custodian_expense` | F1 – Head Office expense analysis | head office | custodian × category pivots, and the transposed variant |
| `advance_register` | F4 – advances register | — | recognised, analysis not implemented yet (HTTP 422 with an explicit message) |

An unrecognised workbook is refused, never guessed. Files are never combined automatically: F1, F2 and F3 are three separate analyses
until the owner confirms two files cover the same scope.

## API
`POST /api/analysis/custody/datasets` (analyst; multipart `file`, optional `year`, `layout`, `scope`) · `GET .../datasets`, `.../{id}` ·
`GET .../{id}/report?lang=ar|en` (JSON) · `.../{id}/report.pdf` · `.../{id}/report.xlsx` (viewer) · `DELETE .../{id}` (admin).
Settings (admin to change): `GET/PUT /api/settings/custody.thresholds`, `custody.display_taxonomy`, `custody.branch_key`.
Holder/custodian names are personal data: the holder section and tables exist only in reports requested by an admin.

## Guarantees
* Source file stored untouched (sha256); every fact keeps its `source_ref` (sheet!cell or row). Blank ≠ 0; explicit zeros only appear as branch "presence".
* Nothing is corrected: row totals that disagree with their components, subtotal rows, stray cells, month-label differences, cost-centre/branch
  spelling conflicts, negative/reclass lines, hard-coded totals → listed in *Data quality*, together with a control-total table (file's stated total vs computed).
* A dimension the file lacks (year, branch, category, scope split) produces an explicit "not supported by this file" line instead of a number.
* Original category/branch names are never altered. Naming variants are *detected* (e.g. `Public Relation` / `Public Relations`) and shown as a grouping
  **suggestion**; only a group approved through `custody.display_taxonomy` produces an additional "by display group" table. Variants are not compared month-to-month.
* Branch groups (e.g. "فروع قنا") stay groups: listed separately, never in the branch ranking, never allocated.
* Branch identity: resolved via `entity_alias` when the branch master knows the name; otherwise cost-centre code (setting `custody.branch_key`: `cost_center` | `name`), else the name as written. Unresolved names are reported. Codes are never generated.
* A period whose branch names barely overlap the others (e.g. a sheet re-typed in another language) is excluded from branch-level change tests and flagged.

## Outlier thresholds
Shipped only as *initial values* in `thresholds.yaml`; the effective values are the setting `custody.thresholds`
(`PUT /api/settings/custody.thresholds`, admin, no redeploy). Every report lists the values used and whether they are still the defaults.
Rules: month-on-month change (total/category/branch/scope), new spend, month vs average of other months, branch total above a Tukey fence,
one line carrying a large share of its category, repeated identical amounts, negative/reclass lines, branches that start/stop spending.

## Report
Sections: executive summary (KPI cards, metric-bound statements, key observations, caveats) · spend & trend · by category (Pareto, heatmap,
category×month, sub-items, approved groups) · Head Office vs branches · branches (ranking, top-N, branch×category, statistics, groups) ·
variances (waterfall, change by category/branch) · unusual items · data quality & coverage (caveats, unsupported list, control totals, issues,
suggested groups, settings used) · custodians (admin only). Arabic (RTL) and English. Executive-summary sentences are generated from computed
metrics only (each carries its metric id in `report.meta.summary_items`).

## Web dashboard (interim UI, no build step)
Served by the API at **`/app/`** (`backend/app/web`: plain HTML/JS, Chart.js vendored under `web/vendor`, so it works offline). It renders the same
report model as the PDF/Excel exports, so the screen and the downloads always agree.
* Upload an Excel file (button or drag-and-drop; optional year when the file does not state one) → analysed immediately; a file already uploaded is simply opened.
* Tabs = report sections: summary (KPI cards, metric-bound statements, key observations, caveats) · trend · categories (Pareto, category×month heatmap, tables) ·
  Head Office vs branches · branches (top-N, branch×category matrix, ranking, groups) · variances (waterfall) · unusual items · data quality (control totals, issues) · custodians (admin).
* Filters: period, branch (searchable), category (searchable) — applied **on the server**, so every KPI, table, chart, PDF and Excel download reflects the current selection.
  Click a category/branch in a chart or heatmap to drill into it; chips show and remove active filters. File control totals are whole-file only and are hidden while filtered.
* Tables: sortable, searchable, "show all". AR/EN toggle (RTL/LTR). Token dialog for `API_TOKENS` deployments. Light/dark follows the system.
* `GET .../report`, `.pdf`, `.xlsx` accept repeatable `period=2026-03`, `branch=<key>`, `category=<name as written>`.

Run locally: `alembic upgrade head && uvicorn app.main:app --reload` → open <http://localhost:8000/app/>. The Next.js frontend planned for Phase 2 would replace this UI and
consume the same API.

## Not yet
PowerPoint export; advance-register analysis (F4, deliberately not started); combined reports (needs the owner's confirmation); a branch alias-mapping screen
(F2 February's English branch names stay flagged for review — no mapping is guessed).
