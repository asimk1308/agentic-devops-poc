#!/usr/bin/env bash
# Starts the Order Service (Spring Boot) and Prometheus, both natively
# (no Docker yet — see PLAN.md Section 18). Idempotent: skips anything
# already listening on its port.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh

if lsof -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "order-service already running on :8080"
else
  echo "starting order-service on :8080 ..."
  (cd demo-service && nohup mvn -q spring-boot:run > /tmp/order-service.log 2>&1 &)
fi

if lsof -iTCP:9090 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "prometheus already running on :9090"
else
  echo "starting prometheus on :9090 ..."
  mkdir -p prometheus/data
  (cd prometheus && nohup prometheus --config.file=prometheus.yml \
      --storage.tsdb.path=./data --web.listen-address=:9090 \
      > /tmp/prometheus.log 2>&1 &)
fi

echo "waiting for both to become ready..."
for i in $(seq 1 30); do
  ok=true
  curl -s -o /dev/null http://localhost:8080/actuator/health || ok=false
  curl -s -o /dev/null http://localhost:9090/-/ready || ok=false
  if [ "$ok" = true ]; then
    echo "order-service: http://localhost:8080  (try: curl localhost:8080/orders)"
    echo "prometheus:    http://localhost:9090"
    exit 0
  fi
  sleep 1
done
echo "timed out waiting for services — check /tmp/order-service.log and /tmp/prometheus.log" >&2
exit 1
