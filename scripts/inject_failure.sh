#!/usr/bin/env bash
# Spec Section 12 Scenario 3 — Error Regression.
# Restarts the Order Service with FAULT_ERROR_RATE set: that fraction of
# requests get a real 5xx response plus a real ERROR log line
# (FaultInjectionFilter.java) -- not simulated JSON, an actual failing
# request Prometheus's error-rate query and get_recent_errors() will see.
#
# Usage: scripts/inject_failure.sh [rate]   (default: 0.2, the spec's own
# "20% requests throw exception" example; rate is 0.0-1.0)
set -euo pipefail
cd "$(dirname "$0")/.."

RATE="${1:-0.2}"
echo "Injecting ${RATE} error rate into order-service (restart required)..."
FAULT_ERROR_RATE="$RATE" scripts/_restart-order-service.sh
echo "order-service is back up with FAULT_ERROR_RATE=$RATE"
echo "Run scripts/generate_load.py to produce traffic, then check Prometheus / the observability MCP."
echo "Undo with: scripts/clear_faults.sh"
