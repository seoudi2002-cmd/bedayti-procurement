# Module discovery protocol

Rule: **no module is built before its real files have been inspected and its data model approved.** For each module
(printing/copiers, paper, rentals/leases, vehicles/fleet, Aramex/logistics, **financial custody (العهد)**, hotels,
asset maintenance, procurement savings, executive reporting) the same five steps apply:

1. **Receive** representative files (sanitised where possible): at least two periods, one "clean" and one "messy" example, plus any Word/PDF source documents and the people who maintain them.
2. **Profile** each file — `POST /api/intake/profile` or `python -m app.tools.profile_file <file>` (structure only, values hidden): sheets, header rows, merged cells, column types/fill rates, formula errors, Word table signatures, PDF text-layer vs scan. Then a manual read of the business logic.
3. **Write the module brief** (`docs/modules/<module>.md`): what the report answers, grain of one row, keys, measures, periods, the master data it links to (branch/employee/supplier/asset), source quirks, data-quality findings, KPIs and exceptions wanted, open questions. *Unclear fields are listed, not assumed.*
4. **Propose the model** (new tables/columns, mapping source→target, what stays raw/source text, what is derived) — shown for approval before any migration that is not purely additive.
5. **Implement** (YAML module + loader + tests on synthetic data), load the real files locally, report counts/exceptions, then iterate.

## Brief template
```
# <Module> — brief
Purpose / decisions it supports:
Source files (type, owner, frequency, periods covered):
Grain (one row = ...) and natural key:
Links to master data (branch / employee / supplier / asset / department) and how reliable each link is:
Measures and units; currency/VAT treatment; period logic:
Source quirks (merged cells, subtotals, errors, mixed formats):
Data-quality findings:
KPIs wanted:      Exceptions wanted:      Views/reports wanted:
Personal data involved and who may see it:
Open questions:
```

## Priority and what to send first
| Order | Module | Why now | Send first |
|---|---|---|---|
| 1 | **Financial custody (العهد)** | core administrative control: balances, ageing, accountability per holder/branch | the custody ledger/register (2+ periods), the issue/settlement forms, the policy on limits and settlement deadlines, who may hold custody |
| 2 | Printing/copiers + Paper | the PO register already holds paper purchases and copier rental memos | machine list, meter readings or monthly counts, rental invoices, paper issue/allocation lists |
| 3 | Aramex/logistics | recurring service memos already identify the supplier | Aramex statements/invoices (shipments, weights, routes), branch codes used by the courier |
| 4 | Rentals/leases | branch cost normalisation (per m²) | lease register with dates/escalation/areas, monthly rent payments |
| 5 | Vehicles/fleet | | vehicle register, fuel and maintenance logs, driver assignment |
| 6 | Hotels | | bookings/invoices with traveller, dates, rate, purpose |
| 7 | Asset maintenance | | asset register, maintenance tickets/costs |
| 8 | Savings, executive reporting | built on the above | agreed baseline definitions, report layouts/branding |

## Financial custody — preliminary questions (to settle with the files)
Which custody types exist (branch petty cash, personal advances, project advances)? Who may hold one and who approves it? What is the document trail for an issue, an expense, a settlement, a top-up, a return? Is there a limit per holder/branch and a settlement deadline? How are expenses categorised? Are balances reconciled to the general ledger, and by whom? What happens when a holder leaves? Which figures does management want to see (open custody total, ageing buckets, over-limit, unsettled > N days, expense by category/branch)?
