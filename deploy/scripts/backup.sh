#!/bin/sh
# One consistent backup: PostgreSQL dump + the UPLOAD_DIR archive + checksums, in BACKUP_DIR/<UTC timestamp>/. Prunes older than BACKUP_KEEP_DAYS.
# Needs PG* env vars (PGHOST, PGUSER, PGPASSWORD, PGDATABASE), UPLOAD_DIR, BACKUP_DIR.
set -eu
: "${UPLOAD_DIR:?}" "${BACKUP_DIR:?}" "${PGDATABASE:?}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$BACKUP_DIR/$TS"
mkdir -p "$OUT"
pg_dump -Fc --no-owner --no-privileges -f "$OUT/db.dump"
tar -C "$UPLOAD_DIR" -czf "$OUT/uploads.tar.gz" .
( cd "$OUT" && sha256sum db.dump uploads.tar.gz > SHA256SUMS )
pg_restore -l "$OUT/db.dump" > /dev/null          # the dump must be readable
echo "backup ok: $OUT"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"${BACKUP_KEEP_DAYS:-30}" -exec rm -rf {} + 2>/dev/null || true
