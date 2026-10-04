#!/bin/sh
# Container scheduler: one backup shortly after start, then every day at 02:00 UTC. Failures are logged and retried next day.
sh /scripts/backup.sh || echo "backup FAILED at $(date -u)"
while true; do
  now=$(date -u +%s); next=$(date -u -d "tomorrow 02:00" +%s 2>/dev/null || echo $((now + 86400)))
  sleep $((next - now))
  sh /scripts/backup.sh || echo "backup FAILED at $(date -u)"
done
