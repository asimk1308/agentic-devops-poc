#!/usr/bin/env bash
# Shared by inject_latency.sh / inject_failure.sh / clear_faults.sh: kill
# whatever's on :8080 and relaunch it with the env vars the caller has
# already exported (FAULT_LATENCY_MS / FAULT_ERROR_RATE, or neither for
# clear_faults.sh). Not meant to be run directly.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

# `mvn spring-boot:run` is two processes (the mvn wrapper + the java
# child it forks); lsof on :8080 only finds the java child. Killing just
# that pid leaves the mvn wrapper alive for a moment, still writing its
# own "process terminated" line to the *same* log file the next
# invocation's `>` redirect is about to truncate -- a real race that
# corrupted /tmp/order-service.log during Phase 4 testing (see
# docs/learning-notes.md). pkill -f matches both processes by command
# line, and waiting on pgrep (not just the port) confirms both are
# actually gone, not just that the socket closed, before truncating.
if pgrep -f "spring-boot:run" >/dev/null 2>&1; then
  pkill -f "spring-boot:run" || true
  for i in $(seq 1 15); do
    pgrep -f "spring-boot:run" >/dev/null 2>&1 || break
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
