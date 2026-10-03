# Copier / printing-machine analytics (implemented)

Second analysis module on the shared **Management Analytics Platform** (after Financial Custody). Same flow:
**upload → validate → analyze → dashboard → executive report (PDF / Excel)**.

## Sources and their authority
| Source | Role | Used for |
|---|---|---|
| Monthly consumption statement (`.xlsx`), **Part 1** (blocks per machine class/package) | **authoritative – operational** | machines, readings, consumption, included copies, additional copies |
| Supplier **e-invoice** (ETA PDF) | **authoritative – financial** | unit prices (rent per class, additional-copy rate), quantities, totals, taxes |
| Statement **Part 2** (same workbook) and the **Word** statement (`.doc`/`.docx`) | supporting detail | governorate/section, rental value; matched machine-by-machine to Part 1, **never an independent total** |
| Scanned printer **status pages** (PDF, OCR) | **evidence only** | validation: counter vs statement reading. **Never** an input to KPIs, costs, totals or decisions; on conflict the statement and invoice prevail |

Files of one month attach to one **cycle** (period) automatically, in any upload order: statement/Word/invoice by the period they state, scans by the
uploader's year/month or the latest cycle. The original files are stored untouched (sha256); a period accepts one statement, one Word file, one invoice.

## What is calculated
* Fleet by class (mono copiers 5000/10000, printers 3000, colour 1000/2000, colour A3); consumption vs included copies (utilisation, unused included copies);
  additional copies (stated in the statement, re-checked as `max(0, consumption − package)`); machines over their package; under-utilised / almost-unused machines
  (thresholds are settings); top consumers; governorate/section and branch comparison (governorate from Part 2/Word); branch ranking.
* **Costs are allocated from the invoice's own prices**, pre-tax: rent per machine = the class's invoice unit price; additional-copy cost = additional copies × the rate of the
  invoice line that covers the class. Σ machine costs equals the invoice's total sales. Invoice VAT/withholding are shown at invoice level only (not spread over machines).
* **Reconciliation** (Part 1 ↔ invoice): per rent line (machines vs quantity, amount), per additional-copy line (copies vs quantity, amount), unit price vs Part 2's rental value,
  classes with no invoice line, expected total sales (statement quantities × invoice prices) vs invoiced; and the invoice's own arithmetic (qty × price, Σ lines, VAT, withholding, grand total).
* **Trend** (item "Σ" appears when ≥ 2 months are uploaded): per-month machines, consumption, utilisation, additional copies, cost, invoice total, MoM; reading continuity
  (a machine's previous reading must equal last month's current reading).

## Paper consumption (distribution statement)
**Source:** the paper distribution statement (`.xlsx`, one purchase order; detected by its title, not by its name). It spans several months, so it belongs to no monthly cycle: item id `paper`
(all purchase orders) or `paper:<dataset>` (one). **Definition (owner):** distribution = consumption; cost = cartons × the carton price of the purchase window; paper is VAT-exempt, so the price is final.
A carton = 5 reams × 500 = 2,500 sheets (A4 80 g). The **need implied by the machines** is a separate estimate (machine pages ÷ pages-per-sheet ÷ sheets-per-carton) and never replaces the distributed consumption.

**Reader:** title → PO number, receipt date, cartons received; rows (م / عدد / فرع / تاريخ); the file's own monthly subtotals and grand total. Controls: lines vs stated monthly subtotals, vs stated total, vs cartons received in the title.
Flagged, never fixed: gaps / out-of-order running numbers, same branch twice on the same day (kept), head-office label spelling variants, dates before the receipt date, missing dates.
**Head Office:** any label starting with «المركز الرئيسي» is a head-office unit; each department (text after the prefix) is reported separately, spelling variants grouped by that text.

**Outputs:** KPIs (cartons, sheets, cost, units, head-office share, monthly average, PO control) · monthly cartons/cost/MoM · units × month tables (cartons and cost) with share and cumulative share · head-office departments × month ·
monthly comparison with the machine pages of months that have a consumption statement (pages per distributed carton, paper cost per page, estimated need, distributed-vs-need) · unit-level comparison where the branch can be linked
(through the official branch register when it knows the name, else an identical normalised name; **no fuzzy matching**, head-office departments are never matched) · PO table, issues and the settings used. Filters: month, unit. With filters the all-machines comparison is not shown.

**Settings** `GET/PUT /api/settings/copier.paper` (admin): `sheets_per_carton`, `pages_per_sheet`, `prices_vat_exempt`, `prices` (date windows, ascending, non-overlapping). Shipped from `paper_defaults.yaml`: the carton size is the owner's figure; **real carton prices are not shipped** (company data) — an admin enters the owner's price windows through the settings API, and until then cost is "not calculated". **`pages_per_sheet` is an initial value (not stated by the owner) and is shown in every report as unconfirmed**. The window boundaries (mid-month) are assumed to fall on the 15th and are editable.
A purchase order whose receipt date falls in no price window gets no cost (never zero).

## Not supported (stated in the report, no substitute figures)
Cost without an invoice; governorate comparison without Part 2/Word; trend with one month; toner/maintenance/downtime; colour/mono split per machine; machine id/serial (identity = class + branch + readings);
right-sizing savings (needs the contract price list).

## Data-quality checks (flag, never fix)
Block without its total row or with a different total; consumption ≠ current − previous; reading decreased; excess ≠ rule; duplicate readings; branch label with a stray "B" marker (shown without it, source kept);
Part 1 machine missing from Part 2/Word and the reverse; value/spelling differences between Part 1 and Part 2/Word; branches not in the branch master; invoice lines/totals that do not add up; invoice lines whose tax detail splits across pages.

## Settings (no code change)
`GET/PUT /api/settings/copier.thresholds` (admin): `low_utilization_pct`, `very_low_utilization_pct`, `high_excess_pct`, `top_n`, `mom_change_pct`, `min_months_for_trend`, `reconcile_tolerance`.
Shipped values are initial defaults awaiting confirmation; each report lists the values used.

## Reusable architecture (what future modules plug into)
`app/core/analysis` (adapter protocol + registry) · generic API `/api/analysis/{module}/datasets…` (upload, list, report JSON/PDF/Excel, filters declared by the module) ·
module-agnostic dashboard shell (`/app/`, module tabs, filter dimensions from `report.meta.filters.dimensions`, multi-file upload, background-processing poll) ·
`ReportModel` + PDF/Excel exporters · settings store with per-module thresholds · `AnalysisCycle` for modules whose month is made of several files.
A new module = parsers + engine + report builder + adapter registered in `app/core/analysis/registry.py`.

## API
`POST /api/analysis/copiers/datasets` (analyst; any of: statement `.xlsx`, Word, invoice PDF, scanned PDF; optional `year`, `month`) → the cycle's meta (202 while scans are OCR'd in the background) ·
`GET …/datasets` (cycles + "all" + "paper") · `GET …/datasets/{cycle|all}` · `…/report?lang=ar|en&governorate=…&branch=…&class=…` · `…/report.pdf` · `…/report.xlsx` · `DELETE …/{cycle}` (admin).
