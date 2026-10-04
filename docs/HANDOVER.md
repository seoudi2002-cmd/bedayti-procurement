# Final production handover and platform freeze

**Status: FROZEN at the commit that adds this document on branch `claude/epic-clarke-xvsry2`** (the tag `platform-freeze-v1.0` could not be pushed from the build environment: create it on that commit). From this point only defects (wrong numbers, crashes, security) are fixed; no new features, modules or report sections are added without a new owner decision.

## 1. What the platform is
One management data-analysis and reporting platform: upload a management file → recognise → validate → analyse → dashboard → executive report (PDF / Excel). Analysis only: no workflow, no approvals, no ERP functions. Every module is an adapter + reader + engine + report builder + settings (`docs/PLATFORM_SCOPE.md`, `docs/ARCHITECTURE.md`).

| Area | Module (API key) | Document |
|---|---|---|
| Financial custody (F1–F4, advances) | `custody` | `docs/CUSTODY_ANALYTICS.md` |
| Copiers / printing + paper | `copiers` | `docs/COPIER_ANALYTICS.md` |
| Aramex shipping | `aramex` | `docs/ARAMEX_ANALYTICS.md` |
| Procurement registers | `procurement` | `docs/PROCUREMENT_ANALYTICS.md` |
| Rent, vehicle fleet, overtime (versioned operating data) | `rent`, `vehicles`, `overtime` | `docs/OPERATING_MODULES.md` |
| Annual administrative operating-cost report | `annual` (`y:YYYY`) | `docs/OPERATING_MODULES.md` |
| Reference library (asset register, regulations; versioned) | `/api/reference` | `docs/REFERENCE_LIBRARY.md` |

## 2. Running it
* Python 3.11, PostgreSQL 16 (SQLite only in tests). `cd backend && pip install -e .` · `alembic upgrade head` (head = **0011**; upgrade → downgrade 0010 → upgrade and `alembic check` were verified clean) · `uvicorn app.main:app`. Dashboard at `/app/`.
* Environment (`app/config.py`): `DATABASE_URL`, `UPLOAD_DIR` (original files are kept here), `MAX_UPLOAD_MB`, `API_TOKENS="token:role[:name],…"` with roles `viewer` (read, reports) · `analyst` (+ upload) · `admin` (+ settings, personal data). Without tokens configured the API is open: **set tokens in production**.
* Tests: `cd backend && pytest -q` → **208 passed**. Run them with `API_TOKENS`, `DATABASE_URL` and `UPLOAD_DIR` unset.
* Back up the PostgreSQL database **and** `UPLOAD_DIR` together (the database holds the parsed versions, the folder holds the original files they came from).

## 3. Rules that hold everywhere (do not change)
1. Source files are kept untouched; every figure traces to a source row; missing is never zero; nothing is guessed — an attribution without evidence is «Unallocated / needs review».
2. **Anything that changes over time is versioned**: a new file adds a version, old versions and the change log stay, the *current view* is the only thing that changes. Nothing is deleted from the API (409).
3. Thresholds, prices, aliases and Head Office rules are **settings** (dashboard ⚙ or `PUT /api/settings/…`, admin, recorded by name), never code; every report states the values used.
4. Personal data (employee, landlord, driver names; notes naming people) is admin-only.
5. Overtime has no amounts: it is reported in hours and is **never** added to the money cost. Operating cost = rent + fleet over the months complete in both.
6. Real company files, names, plates and amounts are never committed; reports are generated on demand.

## 4. Final report package (outside the repository: it contains real company figures)
Generated from the live run on the real files, from this code (commit `561a517`, no report code changed since). They are **the** final set; nothing is regenerated for the handover. Checksums are in the package's `MANIFEST.sha256`.

| File | Content |
|---|---|
| `annual_y-2026.pdf / .xlsx` | Annual report 2026 |
| `annual_y-2025.pdf / .xlsx` | Annual report 2025 |
| `rent_all.pdf / .xlsx` | Rent module report (all data) |
| `vehicles_all.pdf / .xlsx` | Vehicle fleet report (all data) |
| `overtime_all.pdf / .xlsx` | Overtime report (all data) |

**Superseded — do not use:** the first-round `rent_report_ar`, `vehicles_report_ar`, `overtime_report_ar` files (PDF/Excel). They predate the evidence-based resolution of the «منشأة العماري» contract (the rent total then counted that contract twice: 1,891,623.16 instead of **1,890,123.16** for September 2026) and the plate-alias link of vehicle 9412. Any copy of them on a desktop should be archived, not delivered.

Dashboard and annual report were checked month by month against each other on the real files: **0 differences** (rent, fleet, overtime, combined total, per-month values).

## 4b. Deployment status
Nothing is deployed: there is no production URL, host or admin account yet (the build environment has no hosting and no Docker daemon). Everything needed is prepared in `deploy/` and `docs/DEPLOYMENT.md` (compose stack with HTTPS proxy, secrets generator, scheduled backup, restore, smoke test, alias script). The production-mode behaviour (fail-closed auth, roles, persistence across restart, versioning, backup → wipe → restore, settings kept in the database) was verified on PostgreSQL + uvicorn with `APP_ENV=production`; the Docker images themselves could not be built or run here.

## 5. Known limits and open decisions (not blockers)
* **Not available by design:** actual rent paid and the reason for a change; vehicle register (model year, chassis, licence/insurance dates → no renewal alerts); measured fuel quantity; overtime cost and attendance; data before the first month in each file.
* **Needs the owner's inputs:** the vehicle plate alias for the 9412 car must be entered in ⚙ on the production system (the live-run setting was local); overtime for March 2025 (the existing sheet is a copy of February and is excluded); rent months Aug–Dec 2025 hold only Head Office entries (partial, left out of comparisons); stated totals in the files that do not match their parts are listed in each report's quality section, not corrected.
* **Not done:** the annual *document* of the organisation (475 MB scanned PDF) was never readable here; the authority matrix referenced by the regulations was not supplied; the updated asset register will arrive as version 2. The assistant over regulations/data is a later phase.
* A newer file decides the current value by **upload order**, not by data date: upload a corrected file after the one it corrects.
* Optional later decision (not built): an overtime hourly-value setting, only if the owner supplies a real value.

## 6. Freeze policy
Freeze point: the commit adding this document on branch `claude/epic-clarke-xvsry2` (tag it `platform-freeze-v1.0`). Changes after the tag: defect fixes only, each with a test and a changelog line; a new module, report section or setting needs a written owner request.
