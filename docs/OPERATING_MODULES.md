# Rent, vehicles and overtime — operating data kept as history

These three modules analyse **operating data that changes over time**. They share one rule for the whole platform:
**anything that changes over time is a time series (versioned), not a number that gets replaced.**
A new file adds a version; the old versions stay; the system can say what a value was in any month and when it changed.
(Analysis only — upload → recognise → validate → analyse → dashboard → PDF/Excel. No workflow.)

## How history is kept (all three)
* Each uploaded file is one **version** (`analysis_dataset`, upload order). Its values are stored as **append-only** `op_record` rows tied to that version
  (`kind`, `entity_key`, `period` = `YYYY-MM`, `values`, `personal`, `flags`). Nothing is overwritten or deleted; `DELETE` returns 409.
* The **effective** value of an (entity, period, field) comes from the **most recently uploaded** file that states it; a field a newer file does not state
  keeps the older value. Every difference between two consecutive versions is listed (**Versions and changes** section: item, month, field, old, new, from file, to file).
* The same file twice → 409. A file of the wrong kind → 422.
* A value the file does not state is `None` («no entry» / «not available»), never 0. A month without a sheet/column is «not available», not zero.
* Personal data (employee names, landlord names, driver names, notes that mention people) is admin-only; others see codes.
* All thresholds are settings (`GET/PUT /api/settings/{rent|vehicles|overtime}.thresholds`, admin); each report states the values used.

## Rent (`rent`) — `app/modules/rent_analysis`
* **File:** the contract workbook — one sheet per governorate + Head Office; contracts in rows; monthly rent in columns (found by header text).
* **What the file shows:** the governorate sheets repeat one master list; each sheet's footer total adds up **its own** contracts with a formula (`=SUM(AO4+AO5+…)`).
  That formula is the file's explicit statement of which contracts belong to the governorate, so it decides the governorate; the contract's own copy in that sheet is the
  one used; copies in the other sheets are stale duplicates and are not added (differences are counted and reported). No explicit evidence → **Unallocated / needs review**.
* **Measure:** monthly rent as recorded; «_____» = no payment recorded (not zero; quarterly/irregular payers keep their payment months, nothing is spread). A month in which only a few
  contracts have an entry (e.g. a sheet has no column for it) is **partial** and left out of comparisons.
* **Outputs:** rent per month / governorate / branch; month-on-month and year-on-year; rent changes (regular increases vs large jumps); contracts ending soon; periodic payers; advance and deposit as stated;
  reconciliation of the file's own governorate sub-totals with the computed ones; versions and changes.
* **Not available:** what was actually paid; why a rent changed (annual increase vs amendment); area / price per metre; anything before the first month in the file.
* **Observations reported, never fixed:** unreadable dates, date cells whose day/month order cannot be confirmed, header typos (placed by sequence), columns without a header,
  stale copies, sub-totals that do not match their contracts.

## Vehicles (`vehicles`) — `app/modules/vehicle_analysis`
* **Files (three layouts, .xlsx or .xls):** the monthly **repairs statement** (cost per vehicle per month: maintenance categories, fuel cost, totals, distance; a half-year sheet and an insurance-claim table),
  the **usage report** of a vehicle (daily odometer, fuel taken), and the **maintenance card** (odometer and service-due readings).
* **Vehicle identity:** the plate as written. Spellings are linked only by exact match, by a digits-only source whose number is unique, or by an approved alias
  (`PUT /api/settings/vehicles.plates`, e.g. `"ع ن 3333=ع م 3333"`); otherwise they stay separate and are listed as candidates with the evidence (months in which the distance matched).
* **Costs:** the stated maintenance total, fuel cost and grand total are kept as written and compared with their parts; differences are shown. The fuel **quantity** in the repairs statement is
  derived (cost ÷ the price written in its own formula), labelled as such and never used for consumption; consumption (km/L) is computed only from the usage report's own distance and fuel.
  Cost per km uses only vehicle-months that have a distance.
* **Outputs:** cost per month / vehicle / cost item; outlier vehicle-months; distance compared across sources; service items due (from the card); insurance claims; data coverage; versions and changes.
* **Not available:** a vehicle register (model year, chassis, licence and insurance dates) → no renewal alerts; measured fuel quantity and the real price per litre; data before the first month in the files.
* **Observations reported, never fixed:** stated totals that differ from their parts (rows, month total rows, the half-year sheet), titles that disagree with the sheet name, a distance repeated from the previous month,
  unfilled card months (odometer 0), a date cell that advances by a day per sheet.

## Overtime (`overtime`) — `app/modules/overtime_analysis`
* **File:** the monthly statement — one sheet per month, one row per employee; missions (day/night), meals, overtime hours (day/night, each with its weighted value), totals; an annual `report` sheet adds the months by formula.
* **Period:** the month and year written in the **title** inside each sheet (sheet names are labels only). A sheet that repeats another sheet's title period row for row is excluded and reported; two sheets with the
  same period but different data are a conflict (the first is used, flagged critical).
* **Measure:** hours as in the statement; «weighted» is the statement's own value, checked against the multipliers the file itself states. **No amounts, no salary, no attendance** exist in the file → nothing is converted
  to money and no attendance analysis is made. A listed employee with no entry is «no entry», not zero.
* **Outputs:** month-on-month and annual cumulative; day/night split; per-employee totals and concentration; employee × month heatmap; months far above the employee's own average; the annual sheet's totals vs the months read; versions and changes.
* **Not available:** cost of the overtime; attendance / working hours; employee department or branch; reason for the overtime.

## Conflicting copies, exclusions and corrections (rent / overtime)
* **Evidence first, never a guess.** When copies of a rent contract differ, the record proven by a sub-total formula (or agreeing with the other copies) is used. An undated master row whose name matches exactly one dated contract
  and whose recorded months are identical is folded into that dated record; values a copy states before the contract's start date are not used. What cannot be settled is **excluded from every figure** and listed in the
  quality section with each conflicting value and its source sheet/row («Excluded — needs review»).
* **Excluded overtime sheets** (a sheet that repeats another sheet's data under the same title month) enter no figure; the month stays «not available». When the correct month is uploaded later it is stored as a new version, becomes
  available in the current view, and every earlier version stays on record.
* A correction never deletes or replaces history: the current view changes, the versions and the change log do not.
* **Plate aliases are a setting** (`vehicles.plates`, edited from the dashboard ⚙ dialog by an admin, or `PUT /api/settings/vehicles.plates`); removing an alias separates the vehicles again — stored records are never rewritten.

## Annual report (`annual`) — `app/modules/annual_report`
A management report that links the three modules for a year (`y:YYYY`); it stores nothing and has no upload. It calls the same `service.load` / `engine.analyze` as the module dashboards and slices their monthly series to the year,
so the report and the dashboards show the same numbers from the same source.
* **Administrative operating cost (money) = rent + fleet (maintenance + fuel as stated)**, summed over the months in which **both** are complete. **Overtime is shown in hours beside it and is never added** (the statement has no amounts or hourly value).
* Sections: executive summary · operating cost and its monthly trend · rent · fleet · cost per vehicle · overtime · month-on-month / year-on-year comparisons (only where both periods have data) · top cost drivers (shares of the combined total
  and of their component) · biggest increases and decreases · signals for review / cost-saving opportunities (drawn from the figures: contracts nearing expiry, highest regular increases, highest cost per km, outlier months, claims the company bore,
  overtime far above an employee's average — **signals, not recommendations or savings estimates**) · KPIs per module · data quality, exceptions and **what is not in the official figures** (partial / missing months, excluded sheets and contracts,
  unlinked plates, mismatching stated totals — each with its effect) · version history and latest changes.
* Settings: `annual.thresholds` (top_n, move_n, signal_n, mom_change_pct); each module's own thresholds apply to its part; all are listed in the report.

## Dashboard / API
`/api/analysis/{rent|vehicles|overtime}/datasets[/{all|m:YYYY-MM}[/report|report.pdf|report.xlsx]]` (upload: analyst; reports: viewer). `all` = everything recorded; `m:YYYY-MM` = a snapshot up to that month
(annual cumulative included). Filters: governorate / contract (rent), vehicle (vehicles), employee (overtime).

Counts, ratios and structure only are documented here: real files, names and amounts are never committed.
