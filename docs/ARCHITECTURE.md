# Architecture

## Principle
A small generic engine + one configuration package per report type. The core never contains
`if module == "rent"`; everything module-specific lives in `backend/app/modules/<id>/`.

```
file → stage (raw_row, immutable) → map columns → clean/validate → [loader] → facts → KPI engine → insights → dashboards / exports / AI
```

## Module package contract
| File | Purpose |
|---|---|
| `module.yaml` | id (= folder name), name, category, fact tables it writes |
| `schema.yaml` | canonical fields: type, required, dimension link, EN/AR header aliases, derived fields, unique key |
| `kpis.yaml` | declarative KPIs: `aggregate` (sum/avg/count/count_distinct over a fact column) or `ratio` of two KPIs |
| `rules.yaml` | declarative insight rules (evaluated in Phase 4) |
| `loader.py` | `load(session, batch) -> int` (idempotent upsert on the natural key) and optional `rollback(session, batch)` |

`module.yaml` also declares `entity_policy` (create vs review unmatched names per dimension) and `document_types` (the module's document chain).

`ModuleRegistry` validates every package at startup (unknown KPI refs, duplicate fields, id/folder mismatch fail fast).
New module: copy `app/modules/_template`, see its README.
YAML tip: quote aliases containing `#` or `:` (e.g. `"PO #"`).

## Data model (see `app/models`)
- **Meta:** `report_module`, `mapping_template`, `import_batch` (sha256 blocks duplicate uploads), `raw_row` (original + cleaned payload), `validation_issue`.
- **Dimensions (shared):** `dim_period`, `dim_branch` (with `area_m2`, `headcount` for normalisation), `dim_supplier`, `dim_category` (hierarchy), `dim_item`, `dim_asset` (copier/vehicle/lease), `dim_cost_center`, `entity_alias` (messy text → canonical entity, with review status).
- **Procurement documents:** `po_header`, `procurement_case`, `procurement_document`, `document_file` (see `docs/PO_WORKFLOW.md`).
- **Facts:** `fact_cost` and `fact_usage` (conformed, every module writes here → cross-module queries), plus detail: `fact_po_line`, `fact_savings`, `fact_budget`. All carry `batch_id`/`raw_row_id` lineage; deleting a batch cascades, giving rollback.
- **Analytics:** `kpi_value` (cached results with prior period/year/budget), `insight`, `saved_report`, `report_run`.
- JSONB (`attrs`) on dims/facts absorbs module-specific columns without migrations; promote to real columns when queried often.

## Pipeline semantics
1. **Stage:** read CSV (utf-8/cp1256) or XLSX (header-row detection under title rows), store file + raw rows. Nothing is cleaned.
2. **Map:** alias dictionary (EN/AR, Arabic-variant-insensitive, fuzzy ≥ 0.85) suggests `{header → field}`; user confirms; saved as `mapping_template` (UI in Phase 2).
3. **Validate:** per-field cleaning (Arabic digits, `1,234.50`, `(500)`, Excel dates, enums), required checks, derived fields (e.g. `line_amount = qty × price`), duplicate-key warnings. Re-runnable with a corrected mapping.
4. **Load (per module):** entity resolution via `entity_alias` (exact → near-match held for review → create/hold per policy); held rows are loaded after review by re-running load.
5. **KPIs:** computed on demand from facts by `core/kpi/engine.py`; caching in `kpi_value` comes with dashboards.

## Cloud deployment (target)
Containerised API + managed PostgreSQL + object storage for uploads (replace local `UPLOAD_DIR`) + Next.js frontend.
Any container host works (Render, Fly.io, Railway, Azure/AWS/GCP). Single user now: put the app behind the host's
auth or a simple login before exposing it. Roles and branch scoping arrive in Phase 7 (`created_by` columns exist already).
At ~100 branches and thousands of rows/month, plain PostgreSQL is ample; no warehouse needed.

## Phase plan
| Phase | Scope |
|---|---|
| 1 ✅ | Scaffold, schema, registry, ingestion/validation, KPI engine, PO module config |
| 1b ✅ | PO header/lines model, PO loader (upsert, entity resolution + alias review, rollback), procurement case/document graph — see `docs/PO_WORKFLOW.md`. Still open: branch master import, quotation/invoice/payment loaders |
| 2 | Frontend: import wizard, data-quality center, PO dashboards, branch/period comparison; auth (single user) |
| 3 | Add modules: printing, paper, rent, fleet, logistics (mostly YAML + loader) |
| 4 | Insight engine (rules.yaml), cost-driver (price/volume/mix), savings tracker, budget vs actual |
| 5 | Excel / PDF / PowerPoint exporters on `ReportModel` |
| 6 | AI assistant via tool calls (`core/ai/tools.py`), executive summaries |
| 7 | Roles, branch scoping, schedules, audit, backups |

## Known limitations / decisions to revisit
- No auth yet; do not expose publicly until Phase 2 adds it.
- `unique_key` duplicates are warnings only; at load time the last row for a key wins (upsert).
- Rollback removes lines last written by the batch, including ones an earlier batch created and this one refreshed; re-load the earlier file to restore them.
- KPI engine slices by period/branch/supplier/category/item/asset only where the fact table has that column.
- Not tested yet against real Excel exports; mapping aliases are educated guesses until sanitized samples arrive.
