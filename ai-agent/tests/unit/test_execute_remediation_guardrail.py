"""
Regression tests for the defense-in-depth guard added to
nodes/execute_remediation.py: the node itself must refuse to run the one
write action (restart_service) unless state.human_approved is True, even
though routes.route_after_approval is already supposed to be the only
path that reaches this node. execute_restart_service is monkeypatched to
raise if called, so these tests prove the guard short-circuits *before*
touching the real service -- not just that its return value looks right.
"""
import nodes.execute_remediation as execute_remediation_module
from nodes.execute_remediation import execute_remediation


def _forbid_execution(monkeypatch):
    async def _boom():
        raise AssertionError("execute_restart_service must not be called without approval")

    monkeypatch.setattr(execute_remediation_module, "execute_restart_service", _boom)


def test_blocked_when_human_approved_is_false(monkeypatch):
    _forbid_execution(monkeypatch)

    result = execute_remediation({"human_approved": False})

    assert result["execution_result"]["result"] == "BLOCKED"


def test_blocked_when_human_approved_key_missing(monkeypatch):
    _forbid_execution(monkeypatch)

    result = execute_remediation({})

    assert result["execution_result"]["result"] == "BLOCKED"


def test_executes_when_approved(monkeypatch):
    async def fake_restart():
        return {"action": "restart_service", "result": "SUCCESS"}

    monkeypatch.setattr(execute_remediation_module, "execute_restart_service", fake_restart)

    result = execute_remediation({"human_approved": True})

    assert result["execution_result"]["result"] == "SUCCESS"
