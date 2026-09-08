#!/usr/bin/env bash
# Restarts the Order Service with neither FAULT_LATENCY_MS nor
# FAULT_ERROR_RATE set (FaultInjectionFilter.java defaults both to 0/0.0
# -- no injected fault). Also what the AI agent's own RESTART_SERVICE
# remediation action does under the hood (mcp-servers/remediation-server)
# -- the difference here is this is the demo operator resetting state
# between scenarios, not the agent executing an approved remediation.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Clearing injected faults (restart required)..."
scripts/_restart-order-service.sh
echo "order-service is back up with no injected faults."
