"""
Observability MCP server (Spec Section 7, MCP Server 2) -- its 5 tool
functions are plain Python functions (MCPServer.tool() returns fn
unchanged), so these call them directly rather than going through the
MCP stdio transport. httpx calls to Prometheus/Actuator are mocked with
respx so no live infra (scripts/start-infra.sh) is needed.

Section on get_service_metrics: this is the DEGRADED/HEALTHY decision
that draws the line between Scenario 1 (healthy) and Scenario 2 (latency
fault) in docs/demo-script.md -- worth pinning down directly.
"""
import httpx
import pytest
import respx

from tests.conftest import load_mcp_server_module

observability_server = load_mcp_server_module(
    "observability_server_module", "observability-server/server.py"
)


# --- get_application_health -------------------------------------------------

@respx.mock
def test_get_application_health_reports_up():
    respx.get(f"{observability_server.ORDER_SERVICE_BASE_URL}/actuator/health").mock(
        return_value=httpx.Response(200, json={"status": "UP"})
    )

    result = observability_server.get_application_health()

    assert result == {"service": "order-service", "status": "UP"}


@respx.mock
def test_get_application_health_reports_unreachable_on_connection_error():
    respx.get(f"{observability_server.ORDER_SERVICE_BASE_URL}/actuator/health").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    result = observability_server.get_application_health()

    assert result["status"] == "UNREACHABLE"
    assert "error" in result


# --- get_recent_errors --------------------------------------------------------

def test_get_recent_errors_reads_only_error_lines_and_respects_limit(monkeypatch, tmp_path):
    log_file = tmp_path / "order-service.log"
    log_file.write_text(
        "INFO  starting up\n"
        "ERROR first failure\n"
        "INFO  handled request\n"
        "ERROR second failure\n"
        "ERROR third failure\n"
    )
    monkeypatch.setattr(observability_server, "ORDER_SERVICE_LOG_PATH", str(log_file))

    result = observability_server.get_recent_errors(limit=2)

    assert result["count_total"] == 3
    assert result["count_returned"] == 2
    assert result["errors"] == ["ERROR second failure", "ERROR third failure"]


def test_get_recent_errors_missing_log_file(monkeypatch, tmp_path):
    monkeypatch.setattr(observability_server, "ORDER_SERVICE_LOG_PATH", str(tmp_path / "missing.log"))

    result = observability_server.get_recent_errors()

    assert result["errors"] == []
    assert "note" in result


# --- get_service_metrics: the DEGRADED/HEALTHY decision itself --------------

def test_service_metrics_healthy_under_both_thresholds(monkeypatch):
    monkeypatch.setattr(
        observability_server,
        "get_latency_metrics",
        lambda window="5m": {"p95_latency_ms": 200.0, "baseline_latency_ms": 150.0},
    )
    monkeypatch.setattr(
        observability_server, "get_error_rate", lambda window="5m": {"error_rate_percent": 1.0, "window": window}
    )

    result = observability_server.get_service_metrics()

    assert result["status"] == "HEALTHY"


def test_service_metrics_degraded_on_high_error_rate(monkeypatch):
    monkeypatch.setattr(
        observability_server,
        "get_latency_metrics",
        lambda window="5m": {"p95_latency_ms": 200.0, "baseline_latency_ms": 150.0},
    )
    monkeypatch.setattr(
        observability_server, "get_error_rate", lambda window="5m": {"error_rate_percent": 12.0, "window": window}
    )

    result = observability_server.get_service_metrics()

    assert result["status"] == "DEGRADED"


def test_service_metrics_degraded_on_latency_over_2x_baseline(monkeypatch):
    monkeypatch.setattr(
        observability_server,
        "get_latency_metrics",
        lambda window="5m": {"p95_latency_ms": 400.0, "baseline_latency_ms": 150.0},
    )
    monkeypatch.setattr(
        observability_server, "get_error_rate", lambda window="5m": {"error_rate_percent": 0.0, "window": window}
    )

    result = observability_server.get_service_metrics()

    assert result["status"] == "DEGRADED"


# --- get_latency_metrics: PromQL scalar extraction end-to-end ---------------

@respx.mock
def test_get_latency_metrics_extracts_quantiles_from_promql_response():
    def _respond(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("query", "")
        if "0.5," in query:
            value = "0.100"
        elif "0.95," in query:
            value = "0.300"
        else:
            value = "0.500"
        return httpx.Response(
            200,
            json={"status": "success", "data": {"result": [{"value": [0, value]}]}},
        )

    respx.get(f"{observability_server.PROMETHEUS_BASE_URL}/api/v1/query").mock(side_effect=_respond)

    result = observability_server.get_latency_metrics()

    assert result["p50_latency_ms"] == pytest.approx(100.0)
    assert result["p95_latency_ms"] == pytest.approx(300.0)
    assert result["p99_latency_ms"] == pytest.approx(500.0)


@respx.mock
def test_get_latency_metrics_defaults_to_zero_on_empty_result():
    respx.get(f"{observability_server.PROMETHEUS_BASE_URL}/api/v1/query").mock(
        return_value=httpx.Response(200, json={"status": "success", "data": {"result": []}})
    )

    result = observability_server.get_latency_metrics()

    assert result["p50_latency_ms"] == 0.0
    assert result["p95_latency_ms"] == 0.0
    assert result["p99_latency_ms"] == 0.0
