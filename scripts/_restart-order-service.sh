#!/usr/bin/env bash
# Shared by inject_latency.sh / inject_failure.sh / clear_faults.sh: kill
# whatever's on :8080 and relaunch it with the env vars the caller has
# already exported (FAULT_LATENCY_MS / FAULT_ERROR_RATE, or neither for
# clear_faults.sh). Not meant to be run directly.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

pid=$(lsof -tiTCP:8080 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$pid" ]; then
  kill "$pid"
  for i in $(seq 1 15); do
    lsof -tiTCP:8080 -sTCP:LISTEN >/dev/null 2>&1 || break
    sleep 1
  done
fi

(cd demo-service && nohup mvn -q spring-boot:run > /tmp/order-service.log 2>&1 &)

for i in $(seq 1 30); do
  if curl -s -o /dev/null http://localhost:8080/actuator/health; then
    exit 0
  fi
  sleep 1
done
echo "timed out waiting for order-service — check /tmp/order-service.log" >&2
exit 1
