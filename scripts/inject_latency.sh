#!/usr/bin/env bash
# Spec Section 12 Scenario 2 — Latency Regression.
# Restarts the Order Service with FAULT_LATENCY_MS set, so every request
# sleeps that long before responding (FaultInjectionFilter.java). This is
# a real Thread.sleep() on real requests, not simulated metrics -- give
# it one Prometheus scrape interval (5s, prometheus/prometheus.yml) plus
# some real traffic (scripts/generate_load.py) before checking
# get_latency_metrics() / get_service_metrics().
#
# Usage: scripts/inject_latency.sh [milliseconds]   (default: 2000, the
# spec's own Thread.sleep(2000) example)
set -euo pipefail
cd "$(dirname "$0")/.."

MS="${1:-2000}"
echo "Injecting ${MS}ms latency into order-service (restart required)..."
FAULT_LATENCY_MS="$MS" scripts/_restart-order-service.sh
echo "order-service is back up with FAULT_LATENCY_MS=$MS"
echo "Run scripts/generate_load.py to produce traffic, then check Prometheus / the observability MCP."
echo "Undo with: scripts/clear_faults.sh"
