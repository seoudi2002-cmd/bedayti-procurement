#!/bin/sh
# Stores the vehicle plate alias in the PRODUCTION DATABASE (setting vehicles.plates) — the same thing the dashboard ⚙ dialog does.
# Usage: ADMIN_TOKEN=... sh scripts/set-alias.sh https://your.domain
set -eu
URL="${1:?base url}"; : "${ADMIN_TOKEN:?}"
curl -fsS -X PUT "$URL/api/settings/vehicles.plates" -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  --data '{"aliases":["ج ك ق 9412=ج ك ي 9412"]}'
echo
