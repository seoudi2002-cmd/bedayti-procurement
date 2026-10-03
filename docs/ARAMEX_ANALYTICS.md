# Aramex / logistics spend analytics

Analysis only (no shipping workflow): **upload → reconcile → analyze → dashboard → executive report (PDF / Excel)**. Same architecture as the other modules
(`app/core/analysis` adapter, generic API, dashboard shell, `ReportModel` + exporters). Files are stored untouched; nothing is invented; what the files do not
support is shown as «not available».

## Primary goal
At the end of every month, **for each branch**: shipments **sent**, cost of what it sent, shipments **received**, cost of what it received, total shipments,
total Aramex cost and the average cost per shipment — and the same by month, with the change against the previous month (count and cost: value and %).
The main table is `Branch | sent | cost sent | received | cost received | total shipments | total cost | avg` plus a **Head Office** row and an
**Unallocated / needs review** row. Everything else (cities, routes, services, weights, charges, exceptions) is supporting.

## Sources
| File | Role | Gives |
|---|---|---|
| E-invoice PDF (`inv`) | authoritative | invoice number/dates, one line per shipment with the **actual pick-up date**, product code, billed weight, pieces, base / other / net, invoice totals |
| Shipment sheet Excel | authoritative | per AWB: origin, destination, shipper / consignee / contact names, billed + actual weight, tax |
| Contract appendix (scanned PDF) | **reference only** | stored; no figure is read from it. Its rate card is entered by an admin as a setting and only checks that billed base charges follow the card |

The PDF and the Excel of one invoice are linked by the bill document number (either may arrive first; an invoice is analysed once both are present).
The pick-up date comes from the PDF; the Excel's `Airwaybill Date` is not the pick-up date and is not used. Excel `Net Value` is the line total **including tax**
(the invoice's «Net Amount» excludes tax) and `Amount` repeats the base charge; the module states this and never "corrects" the source.
The row whose AWB is text (`TAX Rounding Diff`) is an invoice-level adjustment kept apart from the shipments.

## Allocation (no guessing)
A shipment's whole cost is attributed to its **sender** and, separately, to its **receiver** (never split). Each side is decided only from explicit evidence:
* a party label naming a branch (`<prefix> X`, prefixes in settings) → branch X, confirmed against the **official branch register** when it knows the name
  (read-only lookup: approved alias, identical name, identical name ignoring spaces); a name the register does not know is shown under its own name and listed as *not in the register*;
* **Head Office** = a location / label / contact from the approved Head Office rule (setting `aramex.parties`), matched by identical normalised text;
* branch evidence together with a Head Office marker, or two different branches → **Unallocated (conflicting evidence)**;
* neither → **Unallocated (no branch evidence)**. **A city alone never allocates a branch.**
Unallocated never blocks the module: the report shows the confirmed-allocation rate per side and for both sides, with reasons and cost.
Controls: Σ sent cost = Σ received cost = scope total; Σ counts likewise; no duplicate AWB; Σ shipments = the invoice's stated Total Net Amount.
Because a shipment between two parties is attributed to both, the branches' «total» columns count it twice (stated in the report).

## Items
`all` (every complete invoice, with a party × month matrix) · `m:YYYY-MM` (one month vs the previous month; a month the uploaded invoices do not fully cover is marked *partial*;
if the previous month is not uploaded the comparison is «not available», never zeros) · `inv:<id>` (one invoice with its full reconciliation). Month = pick-up date.
Filters: party, service, city. With filters the invoice controls are not shown.

## Reconciliation (PDF vs Excel, per invoice)
Shipment count; AWBs missing on either side; base, other, net per AWB; billed weight per AWB; Σ base, Σ other; Total Net Amount; VAT and Total vs the sheet (with the rounding adjustment);
the sheet's own total row; origin/destination text (supporting: the PDF truncates long city names). A shipment present in only one source is excluded from the analysis and listed, so the control row shows the gap.

## Supporting analyses and exceptions
Top origin / destination cities and routes, services (product code as printed; its meaning is not documented in the files), billed-weight bands, cost composition (other ÷ base ratio is reported, **not decomposed**).
Exceptions: heavy shipments, billed weight above actual (extra kg; cost impact not available), origin = destination, weekend pick-ups, more than one piece, cost above the norm,
base charge off the contract card (only when a card is entered), conflicting allocation evidence.

## Not available (stated in every report)
Cost by governorate (the files give cities only) · cost by Aramex zone (no approved city→zone table) · rate check without an entered card · comparison with a budget / last year · previous-month comparison when no previous month is uploaded.

## Settings (no code change)
`aramex.thresholds` (`heavy_weight_kg`, `outlier_cost_multiple`, `top_n`, `mom_change_pct`, `low_allocation_pct`, weight bands, weekend days, `reconcile_tolerance`) — initial values awaiting confirmation; each report lists the values used and whether they are defaults.
`aramex.parties` (**admin only**: contains staff names) — `head_office_locations`, `head_office_labels`, `head_office_contacts`, `branch_label_prefixes`. Staff names and real prices are **not shipped** in the repository.
`aramex.rates` — `first_kg`, `additional_kg` (contract card, reference only).

## API
`POST /api/analysis/aramex/datasets` (analyst; PDF, Excel or scanned appendix) · `GET …/datasets` · `GET …/datasets/{all|m:YYYY-MM|inv:id}` · `…/report?lang=ar|en&branch=…&service=…&city=…` · `…/report.pdf` · `…/report.xlsx` · `DELETE …/inv:{id}` (admin).
Reports carry branches and cities only; shipper / consignee person names never leave the server.
