"""
mcp_integrations.tools.investigate_hypothesis's keyword dispatch (Node 4,
Spec Section 11) -- deterministic routing from hypothesis text to which
observability MCP tools get called (Spec Section 22 Principle 1).
mcp_session/call_tool are monkeypatched so no MCP server subprocess is
ever spawned; this tests the dispatch logic, not the MCP transport.
"""
from contextlib import asynccontextmanager

import mcp_integrations.tools as tools_module


@asynccontextmanager
async def _dummy_session(_server_path):
    yield object()


def _recorder(monkeypatch):
    calls: list[str] = []

    async def fake_call_tool(_session, name, arguments=None):
        calls.append(name)
        return {"stub": True}

    monkeypatch.setattr(tools_module, "mcp_session", _dummy_session)
    monkeypatch.setattr(tools_module, "call_tool", fake_call_tool)
    return calls


async def test_database_hypothesis_pulls_recent_errors(monkeypatch):
    calls = _recorder(monkeypatch)

    result = await tools_module.investigate_hypothesis("database connection pool exhausted")

    assert "recent_errors" in result
    assert "get_recent_errors" in calls


async def test_resource_hypothesis_pulls_latency_metrics(monkeypatch):
    calls = _recorder(monkeypatch)

    result = await tools_module.investigate_hypothesis("memory exhaustion under load")

    assert "latency_metrics" in result
    assert "get_latency_metrics" in calls


async def test_deployment_hypothesis_pulls_health_and_github_evidence(monkeypatch):
    calls = _recorder(monkeypatch)

    async def fake_deployment_evidence():
        return {"note": "stubbed"}

    monkeypatch.setattr(tools_module, "get_recent_deployment_evidence", fake_deployment_evidence)

    result = await tools_module.investigate_hypothesis("deployment regression from recent release")

    assert "recent_deployment" in result
    assert result["recent_deployment"] == {"note": "stubbed"}
    assert "get_application_health" in calls


async def test_unmatched_hypothesis_falls_back_to_service_metrics(monkeypatch):
    calls = _recorder(monkeypatch)

    result = await tools_module.investigate_hypothesis("totally unrelated wording")

    assert "service_metrics" in result
    assert calls == ["get_service_metrics"]
