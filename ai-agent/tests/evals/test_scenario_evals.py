"""
Opt-in eval suite -- runs the real graph against a real LLM (Spec
Section 21's 3 demo scenarios + the model-honesty regression, see
tests/evals/dataset.py) with evidence-gathering pointed at a canned
"world" instead of live Prometheus/Order Service, so this is a check of
model *reasoning quality*, not infra availability. Costs tokens; skipped
by default (see pytest.ini's addopts). Run with:

    .venv/bin/pytest -m eval

Needs ANTHROPIC_API_KEY (ai-agent/.env, LLM_PROVIDER=anthropic, the
default -- see llm.py) or a local `ollama serve` with LLM_PROVIDER=ollama.
"""
import os
import uuid
from contextlib import asynccontextmanager

import pytest

import mcp_integrations.tools as tools_module
import nodes.gather_evidence as gather_evidence_module
import nodes.validate as validate_module
from graph.graph import build_graph
from tests.evals.dataset import EVAL_CASES, TOOL_TO_WORLD_KEY, EvalCase

_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
_HAS_LLM_CONFIGURED = (_PROVIDER == "anthropic" and bool(os.getenv("ANTHROPIC_API_KEY"))) or _PROVIDER == "ollama"

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not _HAS_LLM_CONFIGURED,
        reason="no LLM configured -- set ANTHROPIC_API_KEY, or LLM_PROVIDER=ollama with `ollama serve` running",
    ),
]


@asynccontextmanager
async def _dummy_session(_server_path):
    yield object()


def _install_world(monkeypatch: pytest.MonkeyPatch, case: EvalCase) -> None:
    world = case.world

    async def fake_gather_initial_evidence():
        return {
            "health_status": world["health_status"],
            "metrics": world["metrics"],
            "logs": world["logs"],
        }

    async def fake_call_tool(_session, name, arguments=None):
        return world.get(TOOL_TO_WORLD_KEY.get(name, ""), {})

    async def fake_get_recent_deployment_evidence(limit: int = 5):
        return case.deployment_evidence

    async def fake_get_validation_snapshot():
        return {"health_status": world["health_status"], "metrics": world["metrics"]}

    monkeypatch.setattr(gather_evidence_module, "gather_initial_evidence", fake_gather_initial_evidence)
    monkeypatch.setattr(tools_module, "mcp_session", _dummy_session)
    monkeypatch.setattr(tools_module, "call_tool", fake_call_tool)
    monkeypatch.setattr(tools_module, "get_recent_deployment_evidence", fake_get_recent_deployment_evidence)
    monkeypatch.setattr(validate_module, "get_validation_snapshot", fake_get_validation_snapshot)


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c.name for c in EVAL_CASES])
def test_scenario_eval(monkeypatch, case: EvalCase):
    _install_world(monkeypatch, case)

    app = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(
        {"incident_id": thread_id, "incident_description": case.incident_description},
        config=config,
    )

    case.check(result)
