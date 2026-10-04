#!/bin/sh
# Creates .env.production with random secrets (mode 600) and prints the tokens ONCE. Refuses to overwrite.
set -eu
cd "$(dirname "$0")/.."
[ -e .env.production ] && { echo ".env.production already exists: not overwritten"; exit 1; }
DOMAIN="${1:-${DOMAIN:-}}"
[ -n "$DOMAIN" ] || { echo "usage: sh scripts/gen-secrets.sh <domain>   e.g. platform.company.com"; exit 1; }
rnd() { openssl rand -hex 24; }
PG=$(rnd); ADMIN=$(rnd); ANALYST=$(rnd); VIEWER=$(rnd)
umask 077
cat > .env.production <<EOT
DOMAIN=$DOMAIN
POSTGRES_PASSWORD=$PG
APP_ENV=production
MAX_UPLOAD_MB=50
DEFAULT_CURRENCY=EGP
FISCAL_YEAR_START_MONTH=1
BACKUP_KEEP_DAYS=30
API_TOKENS=$ADMIN:admin:owner,$ANALYST:analyst:analyst,$VIEWER:viewer:viewer
EOT
cp .env.production .env   # docker compose reads .env for ${...} substitution
echo "Created .env.production. Save these tokens in a password manager NOW (they are not shown again):"
echo "  admin   : $ADMIN"
echo "  analyst : $ANALYST"
echo "  viewer  : $VIEWER"
