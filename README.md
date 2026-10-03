# Procurement & Administrative Intelligence Platform

Modular reporting and analytics platform: import Excel/CSV per report type, clean and standardize,
compute KPIs, compare branches and periods, find savings, and (later) export executive reports with
AI-assisted summaries. First module: **Purchase Orders & Spend Analysis**.

> **Data policy:** no real company data in this repo. `.gitignore` blocks `*.xlsx`, `*.xls`, `*.csv`
> (except `backend/tests/fixtures/`) and `data/`, `uploads/`. Fixtures must be synthetic or sanitized.

## Layout

```
backend/
  app/
    core/          # generic engine: modules registry, ingestion, cleaning, mapping, KPI, reporting, AI contracts
    models/        # SQLAlchemy schema (meta, dimensions, facts, analytics)
    modules/       # one folder per report type (YAML config + optional loader.py)
    api/           # FastAPI routes
  alembic/         # migrations (0001 = initial schema)
  tests/
frontend/          # Phase 2 (Next.js dashboards) — placeholder
docs/ARCHITECTURE.md, docs/PO_WORKFLOW.md
docker-compose.yml
```

## Run locally

```bash
cp .env.example .env
docker compose up --build          # Postgres + API (migrations run on start) → http://localhost:8000/docs
```

Tests (SQLite, no Postgres needed):

```bash
cd backend && pip install -e ".[dev]" && pytest
```

## Status

**Built:** schema + migrations (0001-0003), module registry with profiles, Excel/CSV intake (module detection, mapping,
validation, merged-cell/subtotal handling), loaders for **branches & regions, employees, suppliers, requisitions,
purchase orders (header-level register + line-level), finance handover**, entity resolution with review queue,
`data_exception` workflow, auditable branch attribution, procurement document graph, KPI engine, role-based API
(viewer/analyst/admin; personal data admin-only).

**Custody analytics dashboard:** open `/app/` on the API (see `docs/CUSTODY_ANALYTICS.md`). **Custody analytics:** see `docs/CUSTODY_ANALYTICS.md`. **Document extraction:** see `docs/DOCUMENT_EXTRACTION.md`. **Not yet:** payment ledger, other modules (see `docs/MODULE_CATALOG.md`, incl. Financial Custody
design), dashboards/frontend, insight engine, report exports, AI assistant, SSO.

Docs: `docs/ARCHITECTURE.md` · `docs/SCHEMA_PROPOSAL_v3.md` · `docs/MODULE_CATALOG.md` · `docs/DOCUMENT_INTAKE.md` ·
`docs/PO_WORKFLOW.md` · `docs/DATA_SOURCES.md`.

## Load order (first time)
`branches` → `employees` → `suppliers` → `requisitions` → `purchase_orders` (profile `register`) → `finance_handover`
(any order works; links and exception states catch up on later loads). Resolve `GET /api/aliases` and review
`GET /api/exceptions` after each load. Set `API_TOKENS` before exposing the API.
