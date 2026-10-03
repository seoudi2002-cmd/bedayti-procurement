# Reference library (versioned reference sources)

Files, regulations and reports the owner supplies are **kept as versioned reference sources** for the whole system (analysis, the annual report, the assistant) — they are not analysed once and discarded.
A new version of a series is **added**; earlier versions stay stored and queryable. The current version is the one with the latest «as of» date (upload order breaks ties); an older export uploaded later does not become current.

## What is stored (`reference_source`)
`kind` (`asset_register` | `regulation` | `annual_report` | `other`), `series_key` (versions of one thing share it), version number, **as-of date** (from the file when it states one, else from the uploader, else none),
the original file (untouched, with its SHA-256; the same file twice is a 409), who uploaded it, notes, and `summary` — what the system understood: profile, observations and, for a later version, the difference from the previous one.

## Asset register (xlsx export of a fixed-asset system) — reference master data
* Detected by its columns (`Asset Number`, `Major Category`, `Original Cost`, …); stored **as received** in `asset_register_row` (one row per asset): description, location text, categories, dates, units, costs, accumulated and net book value,
  the twelve monthly depreciation amounts. Empty cells stay NULL; a date written as text is kept as text and parsed day-first only when unambiguous; the «life» text is not converted; nothing is filled in, corrected or guessed.
* The location text (`Governorate-City-Office-`) is also split into three parts **only when it has exactly that shape**; the text is always kept. Linking offices to the branch master is not done here (no guessing).
* **Observations (never fixes):** duplicate asset numbers (all rows kept), in-service dates stored as text, zero / negative cost, cost ≠ original cost, accounting date after the report period or before the in-service date, in-service after the period,
  net book value ≠ cost − accumulated, «Ytd» ≠ sum of the monthly amounts, columns that are empty on every row, months that are zero for every asset.
* **Profile:** rows, distinct numbers, number range, totals (original / adjusted / recoverable cost, accumulated, YTD, net book value), by category segment / major category / governorate, locations, head-office assets, in-service years,
  period range, fully depreciated count, monthly depreciation totals.
* **Update flow:** upload the updated export → it becomes version N+1 with `diff_vs_previous` (assets added / removed, and how many changed in location, category, description, cost, net book value, units, retirement date); version N stays.

## Documents (regulations, annual report, …) — PDF (scanned or native) or Word
* Stored untouched; the text is read by the existing extraction job (native text layer, else OCR) and stays available **by page** (`/api/reference/{id}/pages/{n}`) with its reading confidence; the version records pages, words, mean confidence, low-confidence and empty pages.
* A document needs a `kind` and a `series` (e.g. `admin_regulation`, `procurement_regulation`, `annual_report`) so later versions are kept together. **No analysis or rules are built on these texts yet**; how they feed the assistant and the reports is decided later.

## API (`/api/reference`)
`POST` (analyst: file, kind?, series?, title?, as_of?, notes?) · `GET` list (viewer; filters kind / series / current_only) · `GET /{id}` (summary) · `GET /{id}/assets` (rows; filters q, location, category; paged) · `GET /{id}/pages/{n}` ·
`GET /{id}/file` (admin: the original) · `PATCH /{id}` (admin: title, notes, as_of only). Versions are never deleted from here.
