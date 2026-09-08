#!/usr/bin/env bash
# Stops whatever start-infra.sh started.
set -euo pipefail

for port_proc in "8080:order-service" "9090:prometheus"; do
  port="${port_proc%%:*}"
  name="${port_proc##*:}"
  pid=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "stopping $name (pid $pid, port $port)"
    kill "$pid"
  else
    echo "$name not running on :$port"
  fi
done
