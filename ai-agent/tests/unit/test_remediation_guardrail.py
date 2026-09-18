"""
Regression tests for the guardrail added to nodes/remediation.py:
`requires_human_approval` must be True whenever `action != "NONE"`,
enforced by RemediationPlan's model_validator rather than trusted from
the LLM's own output (prompts/remediation_planning.md's "always true for
RESTART_SERVICE" instruction is only a prompt -- a weaker/misbehaving
model could set it False, and before this guardrail, nodes/human_approval.py
would then skip the interrupt entirely before a real service restart).
"""
import nodes.remediation as remediation_module
from nodes.remediation import RemediationPlan, plan_remediation


def test_schema_forces_approval_true_for_restart_even_if_llm_says_false():
    plan = RemediationPlan(
        action="RESTART_SERVICE", reason="high latency", risk="MEDIUM", requires_human_approval=False
    )
    assert plan.requires_human_approval is True


def test_schema_leaves_none_action_alone():
    plan = RemediationPlan(action="NONE", reason="healthy", risk="LOW", requires_human_approval=False)
    assert plan.requires_human_approval is False


def test_node_output_has_approval_forced_true_despite_misbehaving_model(monkeypatch, fake_llm):
    misbehaving_output = RemediationPlan(
        action="RESTART_SERVICE",
        reason="latency is high",
        risk="MEDIUM",
        requires_human_approval=False,  # what a weak/misbehaving model might emit
    )
    fake_llm(monkeypatch, remediation_module, misbehaving_output)

    result = plan_remediation({"root_cause": "resource exhaustion", "confidence": 0.9, "evidence": []})

    assert result["remediation_plan"]["action"] == "RESTART_SERVICE"
    assert result["remediation_plan"]["requires_human_approval"] is True


def test_node_output_does_not_force_approval_for_none_action(monkeypatch, fake_llm):
    compliant_output = RemediationPlan(
        action="NONE", reason="metrics are healthy", risk="LOW", requires_human_approval=False
    )
    fake_llm(monkeypatch, remediation_module, compliant_output)

    result = plan_remediation({"root_cause": "no incident", "confidence": 0.95, "evidence": []})

    assert result["remediation_plan"]["action"] == "NONE"
    assert result["remediation_plan"]["requires_human_approval"] is False
