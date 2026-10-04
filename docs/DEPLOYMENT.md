# Deployment (production) — exact steps

Architecture (one small Linux server with Docker): `proxy` (Caddy, automatic HTTPS, the only public ports 80/443) → `api` (the platform, internal only) → `db` (PostgreSQL 16, internal only, named volume `pgdata`); `api` keeps original files in the named volume `uploads`; `backup` runs a dump + uploads archive daily at 02:00 UTC into `deploy/backups/`. Nothing but 80/443 is exposed.

## Prerequisites
A server (Ubuntu 22.04+, 2 GB RAM, 20 GB disk) with Docker + the compose plugin, a DNS name pointing to it (A record), ports 80/443 open.

## Steps
1. `git clone <repo> && cd <repo> && git checkout claude/epic-clarke-xvsry2` (use the freeze commit named in `docs/HANDOVER.md`) · `cd deploy`
2. `sh scripts/gen-secrets.sh platform.yourdomain.com` — writes `.env.production` (mode 600) with a random DB password and **three tokens (admin / analyst / viewer)** and prints them once: store them in a password manager. The file is git-ignored; the app refuses to start outside development without an admin token.
3. `docker compose -f docker-compose.prod.yml up -d --build` — builds, runs `alembic upgrade head`, starts everything. First start takes a few minutes (certificate issuance needs DNS to be correct).
4. Smoke test (read-only, writes nothing): `ADMIN_TOKEN=… ANALYST_TOKEN=… VIEWER_TOKEN=… sh scripts/smoke.sh https://platform.yourdomain.com` → must end with `SMOKE OK`.
5. Plate alias (stored in the production database, not in code): `ADMIN_TOKEN=… sh scripts/set-alias.sh https://platform.yourdomain.com` — or open the dashboard, ⚙ (settings) in the Vehicles tab, paste `ج ك ق 9412=ج ك ي 9412`, Save. Needs the admin token (🔑 button).
6. Upload the real files in each module tab (analyst or admin token): rent, overtime, vehicles (repairs statement, usage report, maintenance card). Then open the Annual report tab.
7. Check backups: `ls deploy/backups/` shows a timestamped folder (db.dump, uploads.tar.gz, SHA256SUMS) a minute after start. **Copy `deploy/backups/` off the server regularly** (e.g. a daily `rsync`/cloud sync) — a backup on the same disk does not survive losing the server.

## Roles
`viewer` reads dashboards/reports (no personal data) · `analyst` also uploads files · `admin` also changes settings and sees personal data (employee / landlord / driver names). Tokens are in `API_TOKENS` (`token:role:name,…`); to rotate, edit `.env.production` and `docker compose … up -d`.

## Restore (tested)
```
cd deploy
docker compose -f docker-compose.prod.yml stop api
docker compose -f docker-compose.prod.yml --profile tools run --rm restore sh /scripts/restore.sh /backups/<timestamp>
docker compose -f docker-compose.prod.yml up -d api
```
`restore.sh` verifies the checksums first, replaces the database and the uploaded files, and the api runs `alembic upgrade head` on start. The same `restore.sh` was drilled in the build environment against PostgreSQL (the compose wrapper itself could not be run there: no Docker daemon): database and files wiped → restored → versions, change log, settings and uploads intact.

## Updating
`git pull` (a frozen release changes only for defect fixes) then `docker compose -f docker-compose.prod.yml up -d --build`. Migrations run automatically; data and versions are untouched (they live in the volumes).

## Not for production
`docker-compose.yml` at the repository root is the development stack (fixed dev password, published DB port): never use it on a server.
