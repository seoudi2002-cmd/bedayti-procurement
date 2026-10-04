#!/bin/sh
# Smoke test of a running instance. READ-ONLY by default (no data is written): health, fail-closed auth, role permissions, settings, module list.
# Usage: ADMIN_TOKEN=.. ANALYST_TOKEN=.. VIEWER_TOKEN=.. sh scripts/smoke.sh https://your.domain
# Add --with-upload ONLY on a staging/test database (uploads a synthetic file twice to check versioning/409).
set -u
URL="${1:?base url}"; FAIL=0
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
check() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 (got $2, want $3)"; FAIL=1; fi; }
check "health"                         "$(code $URL/api/health)" 200
check "no token is refused"            "$(code $URL/api/analysis)" 401
check "bad token is refused"           "$(code -H 'Authorization: Bearer nope' $URL/api/analysis)" 401
check "viewer can read modules"        "$(code -H "Authorization: Bearer $VIEWER_TOKEN" $URL/api/analysis)" 200
check "viewer cannot upload"           "$(code -X POST -F file=@/dev/null -H "Authorization: Bearer $VIEWER_TOKEN" $URL/api/analysis/rent/datasets)" 403
check "viewer cannot change settings"  "$(code -X PUT -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Content-Type: application/json' --data '{}' $URL/api/settings/rent.thresholds)" 403
check "analyst cannot change settings" "$(code -X PUT -H "Authorization: Bearer $ANALYST_TOKEN" -H 'Content-Type: application/json' --data '{}' $URL/api/settings/rent.thresholds)" 403
check "admin can read settings"        "$(code -H "Authorization: Bearer $ADMIN_TOKEN" $URL/api/settings/vehicles.plates)" 200
check "admin can save settings"        "$(code -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' --data '{}' $URL/api/settings/rent.thresholds)" 200
check "dashboard is served"            "$(code $URL/app/)" 200
if [ "${2:-}" = "--with-upload" ] && [ -n "${SMOKE_FILE:-}" ]; then
  check "analyst upload"               "$(code -X POST -F file=@$SMOKE_FILE -H "Authorization: Bearer $ANALYST_TOKEN" $URL/api/analysis/${SMOKE_MODULE:-rent}/datasets)" 201
  check "same file twice is 409"       "$(code -X POST -F file=@$SMOKE_FILE -H "Authorization: Bearer $ANALYST_TOKEN" $URL/api/analysis/${SMOKE_MODULE:-rent}/datasets)" 409
  check "report json"                  "$(code -H "Authorization: Bearer $VIEWER_TOKEN" "$URL/api/analysis/${SMOKE_MODULE:-rent}/datasets/all/report?lang=ar")" 200
  check "report pdf"                   "$(code -H "Authorization: Bearer $VIEWER_TOKEN" "$URL/api/analysis/${SMOKE_MODULE:-rent}/datasets/all/report.pdf?lang=ar")" 200
  check "history is never deleted"     "$(code -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" $URL/api/analysis/${SMOKE_MODULE:-rent}/datasets/all)" 409
fi
[ $FAIL = 0 ] && echo "SMOKE OK" || { echo "SMOKE FAILED"; exit 1; }
