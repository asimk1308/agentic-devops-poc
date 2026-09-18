"""
Opt-in integration tests for the observability MCP server, run over the
real MCP stdio transport against live infra (scripts/start-infra.sh) --
complements the mocked tests/unit/test_observability_server.py, which
covers the same decision logic without needing Prometheus/Order Service
running. Skipped by default (see pytest.ini's addopts); run explicitly:

    .venv/bin/pytest -m integration
"""
import pytest

from mcp_integrations.client import OBSERVABILITY_SERVER, call_tool, mcp_session

pytestmark = pytest.mark.integration


async def test_get_application_health_reachable():
    async with mcp_session(OBSERVABILITY_SERVER) as session:
        result = await call_tool(session, "get_application_health")

    assert result["service"] == "order-service"
    assert result["status"] in ("UP", "DOWN", "UNREACHABLE", "UNKNOWN")


async def test_get_service_metrics_shape():
    async with mcp_session(OBSERVABILITY_SERVER) as session:
        result = await call_tool(session, "get_service_metrics")

    assert result["status"] in ("HEALTHY", "DEGRADED")
    assert "p95_latency_ms" in result
    assert "error_rate" in result


async def test_get_recent_errors_shape():
    async with mcp_session(OBSERVABILITY_SERVER) as session:
        result = await call_tool(session, "get_recent_errors", {"limit": 5})

    assert "errors" in result
    assert isinstance(result["errors"], list)
