"""
One test per LLM node (nodes 1/3/5/6) verifying state-shaping logic with
a stubbed LLM (tests/conftest.py's fake_llm fixture) -- no real API
call, no network. Formalizes the manual monkeypatching described in
docs/learning-notes.md's Phase 4 section. Model *quality/behavior* (does
the model reason well, not just does the node plumb its output
correctly) belongs in tests/evals/, not here.
"""
import nodes.evaluate_evidence as evaluate_evidence_module
import nodes.generate_hypotheses as generate_hypotheses_module
import nodes.remediation as remediation_module
import nodes.understand_incident as understand_incident_module
from nodes.evaluate_evidence import RootCauseAnalysis, evaluate_evidence
from nodes.generate_hypotheses import Hypotheses, Hypothesis, generate_hypotheses
from nodes.remediation import RemediationPlan, plan_remediation
from nodes.understand_incident import IncidentUnderstanding, understand_incident


def test_understand_incident_passes_through_structured_fields(monkeypatch, fake_llm):
    fake_llm(
        monkeypatch,
        understand_incident_module,
        IncidentUnderstanding(
            service="order-service", incident_type="performance_degradation", priority="high"
        ),
    )

    result = understand_incident({"incident_description": "orders are slow"})

    assert result == {
        "service_name": "order-service",
        "incident_type": "performance_degradation",
        "priority": "high",
    }


def test_generate_hypotheses_merges_and_sorts_by_confidence_desc(monkeypatch, fake_llm):
    fake_llm(
        monkeypatch,
        generate_hypotheses_module,
        Hypotheses(
            hypotheses=[
                Hypothesis(description="low conf guess", confidence=0.2, investigation="check X"),
                Hypothesis(description="high conf guess", confidence=0.9, investigation="check Y"),
            ]
        ),
    )

    result = generate_hypotheses(
        {
            "incident_description": "orders are slow",
            "hypotheses": [{"description": "prior guess", "confidence": 0.5, "investigation": "check Z"}],
        }
    )

    descriptions = [h["description"] for h in result["hypotheses"]]
    assert descriptions == ["high conf guess", "prior guess", "low conf guess"]


def test_generate_hypotheses_dedupes_by_description_keeping_latest(monkeypatch, fake_llm):
    fake_llm(
        monkeypatch,
        generate_hypotheses_module,
        Hypotheses(
            hypotheses=[
                Hypothesis(description="same guess", confidence=0.8, investigation="refined check"),
            ]
        ),
    )

    result = generate_hypotheses(
        {
            "incident_description": "orders are slow",
            "hypotheses": [{"description": "same guess", "confidence": 0.3, "investigation": "original check"}],
        }
    )

    assert len(result["hypotheses"]) == 1
    assert result["hypotheses"][0]["confidence"] == 0.8


def test_evaluate_evidence_passes_through_root_cause_fields(monkeypatch, fake_llm):
    fake_llm(
        monkeypatch,
        evaluate_evidence_module,
        RootCauseAnalysis(root_cause="database pool exhaustion", confidence=0.85, evidence=["errors spiked"]),
    )

    result = evaluate_evidence({"hypotheses": [], "investigation_results": []})

    assert result["root_cause"] == "database pool exhaustion"
    assert result["confidence"] == 0.85
    assert result["evidence"] == ["errors spiked"]


def test_plan_remediation_passes_through_none_action(monkeypatch, fake_llm):
    fake_llm(
        monkeypatch,
        remediation_module,
        RemediationPlan(action="NONE", reason="metrics are healthy", risk="LOW", requires_human_approval=False),
    )

    result = plan_remediation({"root_cause": "no incident", "confidence": 0.9, "evidence": []})

    assert result["remediation_plan"]["action"] == "NONE"
