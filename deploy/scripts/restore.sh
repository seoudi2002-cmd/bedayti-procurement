#!/bin/sh
# Restore a backup folder (db.dump + uploads.tar.gz). DESTRUCTIVE: replaces the database and the uploaded files.
# Usage:  sh scripts/restore.sh backups/20261004T020000Z      (stop the api first: docker compose -f docker-compose.prod.yml stop api)
# Env for direct use: PGHOST PGUSER PGPASSWORD PGDATABASE UPLOAD_DIR   (compose wrapper below fills them in)
set -eu
DIR="${1:?backup folder}"
[ -f "$DIR/db.dump" ] && [ -f "$DIR/uploads.tar.gz" ] || { echo "not a backup folder"; exit 1; }
( cd "$DIR" && sha256sum -c SHA256SUMS )                      # refuse corrupted backups
: "${UPLOAD_DIR:?}" "${PGDATABASE:?}"
echo "Restoring $DIR into database $PGDATABASE and $UPLOAD_DIR"
pg_restore --clean --if-exists --no-owner --no-privileges -d "$PGDATABASE" "$DIR/db.dump"
mkdir -p "$UPLOAD_DIR"
find "$UPLOAD_DIR" -mindepth 1 -delete
tar -C "$UPLOAD_DIR" -xzf "$DIR/uploads.tar.gz"
echo "restore ok — start the api again (it runs alembic upgrade head on start)"
