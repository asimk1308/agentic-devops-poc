"""
Remediation MCP server (Spec Section 7, MCP Server 3) -- restart_service()
is the one write action in the whole POC. These tests mock subprocess/httpx
so no real process is ever killed or started; they cover its three
possible outcomes (Spec docstring: this server performs no approval
check itself -- that's nodes/human_approval.py's job, see
tests/unit/test_human_approval.py and test_remediation_guardrail.py).
"""
import subprocess

from tests.conftest import load_mcp_server_module

remediation_server = load_mcp_server_module(
    "remediation_server_module", "remediation-server/server.py"
)


def test_restart_fails_when_nothing_listening_on_port(monkeypatch):
    monkeypatch.setattr(remediation_server, "_pid_on_port", lambda port: None)

    result = remediation_server.restart_service()

    assert result["result"] == "FAILED"
    assert "not running" in result["reason"]


def test_restart_fails_when_old_process_does_not_exit(monkeypatch):
    monkeypatch.setattr(remediation_server, "_pid_on_port", lambda port: 12345)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(remediation_server, "_wait_until", lambda predicate, timeout, interval=1.0: False)

    result = remediation_server.restart_service()

    assert result["result"] == "FAILED"
    assert "did not exit" in result["reason"]


def test_restart_succeeds_when_new_process_becomes_healthy(monkeypatch, tmp_path):
    port_states = iter([12345, None])  # first call: old pid present; after "kill", gone
    monkeypatch.setattr(remediation_server, "_pid_on_port", lambda port: next(port_states, None))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(remediation_server, "ORDER_SERVICE_LOG_PATH", str(tmp_path / "order-service.log"))

    wait_calls = {"n": 0}

    def fake_wait_until(predicate, timeout, interval=1.0):
        wait_calls["n"] += 1
        return True  # port freed, then healthy -- both waits succeed

    monkeypatch.setattr(remediation_server, "_wait_until", fake_wait_until)

    result = remediation_server.restart_service()

    assert result["result"] == "SUCCESS"
    assert result["previous_pid"] == 12345
    assert wait_calls["n"] == 2


def test_restart_times_out_when_health_never_comes_back(monkeypatch, tmp_path):
    monkeypatch.setattr(remediation_server, "_pid_on_port", lambda port: 12345)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(remediation_server, "ORDER_SERVICE_LOG_PATH", str(tmp_path / "order-service.log"))

    wait_results = iter([True, False])  # port freed, but health check never succeeds
    monkeypatch.setattr(remediation_server, "_wait_until", lambda predicate, timeout, interval=1.0: next(wait_results))

    result = remediation_server.restart_service()

    assert result["result"] == "TIMED_OUT"
