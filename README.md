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
docs/ARCHITECTURE.md
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

## Status (Phase 1 — foundation)

Done: schema + migration, module registry/contract, upload → parse → map → clean → validate pipeline,
declarative KPI engine, API, Purchase Orders module config, tests.
Not yet: fact loaders & entity resolution (Phase 1b), dashboards, insights, exports, AI, auth.
See `docs/ARCHITECTURE.md`.
