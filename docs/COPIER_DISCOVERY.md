# Copier / Printing-machine analytics — discovery and proposed design (no code yet)

Structure, counts and ratios only; no names, prices or amounts (real data is never committed).
Inputs analysed: one monthly **meter-reading statement** (xlsx), the same statement as a legacy **.doc**, the vendor's **e-invoice** (ETA PDF, 4 pages) and
**47 scanned printer status pages** (PDF). Period: July 2026.

## 1. Data profile
| Source | What it is | Grain |
|---|---|---|
| X – statement workbook (`Sheet1`) | Part 1 (rows 1–268): six blocks, one per **machine class/package** (mono 10000, mono 5000, printers 3000, colour 2000, colour 1000, colour-A3 2000). Part 2 (rows 270+): the same machines **grouped by governorate** with a rental value per machine. | one row per **machine** (branch + class + previous/current reading) |
| W – statement .doc | Part 2 as a Word table (one table per governorate) | same as Part 2 |
| I – e-invoice PDF | Vendor invoice: seller/buyer registrations, 8 lines (rent per class, excess pages per class), VAT 14 %, withholding 3 %, totals | invoice line per class |
| S – status-page scans (47 pp) | Photographed printer "Status Page" printouts carrying the **Printed Pages counter**, print timestamp, branch stamp, handwriting | one page per machine |

Machines: 237 rows (124 five-thousand, 95 printers-3000, 12 ten-thousand, 6 colour). Governorate sections: 16 plus "Administrations".
Columns: seq, branch, previous reading, current reading, consumption, excess, (Part 2 only) machine class, rental value, notes (empty).
No machine id/serial/model, no vendor, no price list, no contract, no branch code in X/W.

## 2. Calculations the sources support (verified on the July file)
* consumption = current − previous: 0 mismatches. excess = max(0, consumption − class allowance): 0 mismatches.
* Rent per machine is a fixed value per class (consistent for all rows of a class).
* **Excess rate per class exists only on the invoice** (mono classes share one rate; colour classes have their own).
* Expected billing = Σ rent per class + Σ excess × class rate **equals the invoice's total sales exactly** (to the piaster), and machine counts per class
  equal the invoice quantities when Part 1 is used.
* Evidence: counters read from the scans match a current reading in the statement for 35 of the 36 pages where a counter was readable (all belong to the 3000-printer class).

## 3. Available KPIs / analysis (single period)
Fleet (machines, by class/governorate/branch/administration); pages consumed vs allowance (utilisation %, distribution bands); excess pages and machines in excess;
rent; excess cost (pages × invoice rate — labelled "allocated from invoice rates"); effective cost per page per class/branch/governorate; unused allowance;
low-use machines; top consumers/excessors; governorate comparison; invoice-to-statement reconciliation (lines, quantities, totals); evidence coverage %.
Illustrative July picture: ≈46 % of purchased allowance unused; 40 of 237 machines above allowance; 42 below 25 % utilisation; two machines at ≈ 0 pages.
**Not supported by the data**: trends/MoM (one period; a previous-reading column is the previous month's closing counter, not its consumption), per-machine cost of VAT/withholding
(invoice level only), toner/maintenance/downtime, colour/mono split per machine, right-sizing savings (needs the contract price list — class prices seen here are one month's evidence).

## 4. Data-quality issues found
Part 1 vs Part 2/W disagree: one 5000-class and one 3000-class machine of one branch are in Part 1 (and on the invoice) but missing from Part 2 and the Word file;
5000-class block has no total row (others total only the excess column); stray "B" letters appended to branch names; branch spelling differs between Part 1 and Part 2
(and between files); person names inside location names; machine class typed as free text for colour machines ("الوان2000-", "1000الوان", …); empty notes column;
period only as free text in a title; no machine identifier (identity = branch + class + previous reading); duplicate scan (same counter twice); 11 scans with no
readable counter; scan timestamps of other events (sanitisation date) next to the print date; .doc is legacy binary (needs a converter); invoice text is stored reversed with Arabic-Indic digits.

## 5. Proposed design inside the platform
Reuse unchanged: analysis dataset registry, settings store (per-module thresholds), report model + PDF/Excel exporters, dashboard shell, entity resolution (branch master via entity_alias),
RBAC, exceptions. Add `copier_analysis` as an **analysis module** with: layout parsers (statement-by-class, statement-by-governorate, Word statement, e-invoice, status-page evidence),
module facts (`copier_reading_fact`, `copier_invoice_line_fact`, `copier_evidence_fact`), a **monthly cycle** that ties the files of one period together (statement ↔ invoice ↔ evidence — here combining is the point), and analysis/report/dashboard sections.
Generalisation step before coding: make routes `/api/analysis/{module}/…` and the dashboard module-agnostic (it already renders the generic report model).
