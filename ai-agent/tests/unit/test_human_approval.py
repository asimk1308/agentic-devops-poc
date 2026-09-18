"""
Node 7 (spec Section 11) -- verifies the approval interrupt actually
fires when a plan needs it, and is skipped when it doesn't, using a tiny
single-node graph so interrupt()/Command(resume=...) behave exactly as
they do in the real graph (graph/graph.py, main.py) rather than relying
on interrupt()'s internals when called as a bare function outside any
graph execution context.
"""
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from graph.state import IncidentState
from nodes.human_approval import human_approval


def _build_single_node_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("human_approval", human_approval)
    graph.add_edge(START, "human_approval")
    graph.add_edge("human_approval", END)
    return graph.compile(checkpointer=MemorySaver())


def _invoke(app, initial_state):
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return config, app.invoke(initial_state, config=config)


def test_no_interrupt_when_action_is_none():
    app = _build_single_node_graph()
    _, result = _invoke(app, {"remediation_plan": {"action": "NONE", "requires_human_approval": False}})

    assert "__interrupt__" not in result
    assert result["human_approved"] is False


def test_no_interrupt_when_plan_does_not_require_approval():
    app = _build_single_node_graph()
    _, result = _invoke(
        app, {"remediation_plan": {"action": "RESTART_SERVICE", "requires_human_approval": False}}
    )

    assert "__interrupt__" not in result
    assert result["human_approved"] is False


def test_interrupts_when_approval_required():
    app = _build_single_node_graph()
    _, result = _invoke(
        app, {"remediation_plan": {"action": "RESTART_SERVICE", "requires_human_approval": True}}
    )

    assert "__interrupt__" in result


def test_resume_yes_sets_human_approved_true():
    app = _build_single_node_graph()
    config, result = _invoke(
        app, {"remediation_plan": {"action": "RESTART_SERVICE", "requires_human_approval": True}}
    )
    assert "__interrupt__" in result

    resumed = app.invoke(Command(resume="y"), config=config)
    assert resumed["human_approved"] is True


def test_resume_no_sets_human_approved_false():
    app = _build_single_node_graph()
    config, result = _invoke(
        app, {"remediation_plan": {"action": "RESTART_SERVICE", "requires_human_approval": True}}
    )
    assert "__interrupt__" in result

    resumed = app.invoke(Command(resume="n"), config=config)
    assert resumed["human_approved"] is False
