"""
graph/routes.py's two conditional-edge functions are pure -- they only
read numbers/booleans other nodes already wrote to state (Spec Section
22 Principle 1), so no LLM/MCP stubbing is needed at all.
"""
from graph.routes import (
    CONFIDENCE_THRESHOLD,
    MAX_INVESTIGATION_LOOPS,
    route_after_approval,
    route_after_evaluate,
)


def test_high_confidence_proceeds_to_remediation():
    state = {"confidence": CONFIDENCE_THRESHOLD, "investigation_loops": 0}
    assert route_after_evaluate(state) == "remediation"


def test_low_confidence_loops_back_to_investigate():
    state = {"confidence": 0.1, "investigation_loops": 0}
    assert route_after_evaluate(state) == "investigate_more"


def test_loop_cap_forces_remediation_even_at_low_confidence():
    state = {"confidence": 0.1, "investigation_loops": MAX_INVESTIGATION_LOOPS}
    assert route_after_evaluate(state) == "remediation"


def test_missing_confidence_defaults_to_looping():
    assert route_after_evaluate({}) == "investigate_more"


def test_approved_plan_executes():
    assert route_after_approval({"human_approved": True}) == "execute"


def test_rejected_plan_skips_execution():
    assert route_after_approval({"human_approved": False}) == "skip_execution"


def test_no_approval_recorded_skips_execution():
    # e.g. human_approval never ran an interrupt (NONE action, or a plan
    # that didn't require approval) -- state has no human_approved key.
    assert route_after_approval({}) == "skip_execution"
