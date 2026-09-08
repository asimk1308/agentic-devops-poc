"""
Observability MCP server (Spec Section 7, MCP Server 2).

Spec Section 6: "The AI agent should retrieve operational information
through tools rather than directly reading arbitrary files." This server
is that boundary — it wraps Prometheus (for metrics/latency/error-rate)
and the Order Service's own Actuator + log file (for health/recent
errors), and exposes them as five read-only tools. Every tool here is
safe to call autonomously (Spec Section 22, Principle 3: reads need no
approval; only Section 9's remediation-server actions do).

Run manually to verify (this file is normally spawned as a subprocess by
an MCP client, same pattern as ai-agent/step3_mcp_basics):
    ai-agent/.venv/bin/python mcp-servers/observability-server/test_client.py

Requires the Order Service + Prometheus running (scripts/start-infra.sh).
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# Loads ai-agent/.env even though this file lives outside ai-agent/, so
# the same ORDER_SERVICE_BASE_URL / PROMETHEUS_BASE_URL config is shared
# in one place instead of duplicated per server.
load_dotenv(Path(__file__).parent.parent.parent / "ai-agent" / ".env")

ORDER_SERVICE_BASE_URL = os.getenv("ORDER_SERVICE_BASE_URL", "http://localhost:8080")
PROMETHEUS_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090")
ORDER_SERVICE_LOG_PATH = os.getenv("ORDER_SERVICE_LOG_PATH", "/tmp/order-service.log")
BASELINE_LATENCY_MS = float(os.getenv("BASELINE_LATENCY_MS", "150"))
SERVICE_NAME = "order-service"

server = MCPServer("observability-mcp")


def _promql(query: str) -> list[dict]:
    """Run a PromQL instant query, return the raw `result` vector."""
    resp = httpx.get(
        f"{PROMETHEUS_BASE_URL}/api/v1/query",
        params={"query": query},
        timeout=5.0,
    )
    resp.raise_for_status()
    body = resp.json()
    if body["status"] != "success":
        raise RuntimeError(f"PromQL query failed: {body}")
    return body["data"]["result"]


def _scalar(query: str, default: float = 0.0) -> float:
    result = _promql(query)
    if not result:
        return default
    return float(result[0]["value"][1])


@server.tool()
def get_application_health() -> dict:
    """Fetch the Order Service's own /actuator/health status."""
    try:
        resp = httpx.get(f"{ORDER_SERVICE_BASE_URL}/actuator/health", timeout=5.0)
        resp.raise_for_status()
        body = resp.json()
        return {"service": SERVICE_NAME, "status": body.get("status", "UNKNOWN")}
    except httpx.HTTPError as exc:
        return {"service": SERVICE_NAME, "status": "UNREACHABLE", "error": str(exc)}


@server.tool()
def get_latency_metrics(window: str = "5m") -> dict:
    """
    p50/p95/p99 HTTP latency (ms) over the given window, via
    histogram_quantile on http_server_requests_seconds_bucket.
    """
    quantiles = {}
    for q in (0.50, 0.95, 0.99):
        query = (
            "histogram_quantile("
            f"{q}, sum(rate(http_server_requests_seconds_bucket"
            f'{{application="{SERVICE_NAME}"}}[{window}])) by (le))'
        )
        value_seconds = _scalar(query)
        quantiles[f"p{int(q * 100)}_latency_ms"] = round(value_seconds * 1000, 1)
    quantiles["baseline_latency_ms"] = BASELINE_LATENCY_MS
    return quantiles


@server.tool()
def get_error_rate(window: str = "5m") -> dict:
    """Percentage of HTTP requests returning 5xx over the given window."""
    total = _scalar(
        f'sum(rate(http_server_requests_seconds_count{{application="{SERVICE_NAME}"}}[{window}]))'
    )
    errors = _scalar(
        f'sum(rate(http_server_requests_seconds_count{{application="{SERVICE_NAME}",status=~"5.."}}[{window}]))'
    )
    error_rate = round((errors / total) * 100, 2) if total > 0 else 0.0
    return {"error_rate_percent": error_rate, "window": window}


@server.tool()
def get_service_metrics(window: str = "5m") -> dict:
    """
    Combined health/error-rate/latency snapshot, in the shape the spec's
    Section 7 example shows — this is the tool an incident-triage node
    would typically call first.
    """
    latency = get_latency_metrics(window)
    error = get_error_rate(window)

    is_degraded = (
        error["error_rate_percent"] > 5.0
        or latency["p95_latency_ms"] > BASELINE_LATENCY_MS * 2
    )

    return {
        "service": SERVICE_NAME,
        "status": "DEGRADED" if is_degraded else "HEALTHY",
        "error_rate": error["error_rate_percent"],
        "p95_latency_ms": latency["p95_latency_ms"],
        "baseline_latency_ms": BASELINE_LATENCY_MS,
    }


@server.tool()
def get_recent_errors(limit: int = 20) -> dict:
    """Tail the Order Service's log file for the most recent ERROR lines."""
    log_path = Path(ORDER_SERVICE_LOG_PATH)
    if not log_path.exists():
        return {"errors": [], "note": f"log file not found at {log_path}"}

    error_lines = [
        line.rstrip("\n")
        for line in log_path.read_text(errors="replace").splitlines()
        if "ERROR" in line
    ]
    return {
        "errors": error_lines[-limit:],
        "count_returned": min(len(error_lines), limit),
        "count_total": len(error_lines),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    server.run()  # stdio transport
