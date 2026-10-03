# Platform scope (final) and roadmap

**What this is:** one management data-analysis and reporting platform — upload management files → the system recognises them → validates → analyses → dashboard → executive report (PDF / Excel).
It is **not** an ERP, a document-flow or a purchasing/custody workflow system. Every module follows the same architecture (adapter + parsers + engine + report builder + settings), so a new file type or module is added the same way.

## Rules that apply to every module
* Source files are kept untouched; every figure traces to a source row; missing is never zero; nothing is guessed (an attribution that cannot be confirmed is shown as «Unallocated / needs review»).
* Thresholds, prices, Head Office rules and similar values are settings (admin, no code change); every report states the values used. Real company data, staff names and prices are never committed.
* Personal data is admin-only. Supporting files (scans, appendices) never change the authoritative numbers.
* The main report of a module is its stated primary goal; extra analyses are supporting and never override it. Nothing is built just because it is possible.

## Files are reference sources, not one-off inputs
Files, regulations and reports the owner supplies are **kept as versioned sources/reference** for later use by the system (analysis, annual report, assistant) — not analysed once and discarded. A newer version of a source is added as a new version; earlier versions stay.

Implemented: `docs/REFERENCE_LIBRARY.md` (versioned reference sources — asset register stored; documents stored with their page text).

## Built (see each module's document)
Financial custody (F1–F4, incl. the temporary-advance register) · Copiers / printing machines (+ paper distribution and consumption) · Aramex shipping (per branch: sent / received, monthly) · Procurement registers (POs, requisitions, suppliers, finance handover) · Rent contracts, vehicle fleet and overtime — operating data kept as versioned history (`docs/OPERATING_MODULES.md`) · Annual administrative operating-cost report linking them · master data (branches, employees, suppliers) · PO document extraction.

## Next phase (in this order; nothing else starts before it is reported)
1. **Asset register** — recorded as core **reference master data**, as received (even if it is not up to date to the end of 2024); no edits, no guessing of missing fields; the updated file later becomes a new version and earlier versions are kept.
2. **Administrative regulation** and 3. **Procurement regulation** — read, structure understood (sections, articles, tables, thresholds/limits, authorities, definitions) and stored as **reference**. **No code is built on them yet**; how they feed the assistant and the reports is decided afterwards.
4. **Annual report** — read and structure understood and stored as reference. Final aim: the system **helps prepare the annual report** from the data of all modules (not only display data). Design decided after the structure is understood.

## Assistant (later)
Answers questions from: the regulations + branch/reference data + operational data + the results of the analyses and reports — each answer grounded in and citing its source; not a general chatbot.
