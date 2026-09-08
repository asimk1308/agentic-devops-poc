"""
Main graph (Spec Section 8/11): wires the nine nodes into the workflow
diagrammed in Section 8, including the Step 13 investigation loop and
the Node 7 human-approval interrupt.

Why a checkpointer? `interrupt()` in nodes/human_approval.py only works
with one -- LangGraph needs somewhere to persist the state snapshot it
unwinds to when a node calls `interrupt()`, so that a *later*, separate
`.invoke(Command(resume=...), config)` call (same thread_id) can pick up
exactly where execution paused instead of restarting the graph from
scratch. `MemorySaver` is in-process/in-memory -- fine for this POC
(one process, one demo run); a real deployment would use a persistent
checkpointer (e.g. Postgres) so approval could survive a restart.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from graph.routes import route_after_approval, route_after_evaluate
from graph.state import IncidentState
from nodes.evaluate_evidence import evaluate_evidence
from nodes.execute_remediation import execute_remediation
from nodes.gather_evidence import gather_evidence
from nodes.generate_hypotheses import generate_hypotheses
from nodes.human_approval import human_approval
from nodes.investigate import investigate
from nodes.remediation import plan_remediation
from nodes.understand_incident import understand_incident
from nodes.validate import validate


def build_graph():
    graph = StateGraph(IncidentState)

    graph.add_node("understand_incident", understand_incident)
    graph.add_node("gather_evidence", gather_evidence)
    graph.add_node("generate_hypotheses", generate_hypotheses)
    graph.add_node("investigate", investigate)
    graph.add_node("evaluate_evidence", evaluate_evidence)
    graph.add_node("plan_remediation", plan_remediation)
    graph.add_node("human_approval", human_approval)
    graph.add_node("execute_remediation", execute_remediation)
    graph.add_node("validate", validate)

    graph.add_edge(START, "understand_incident")
    graph.add_edge("understand_incident", "gather_evidence")
    graph.add_edge("gather_evidence", "generate_hypotheses")
    graph.add_edge("generate_hypotheses", "investigate")
    graph.add_edge("investigate", "evaluate_evidence")

    # Step 13: loop back for another gather/evaluate pass, capped in
    # routes.route_after_evaluate, or proceed once confidence is enough.
    graph.add_conditional_edges(
        "evaluate_evidence",
        route_after_evaluate,
        {"remediation": "plan_remediation", "investigate_more": "generate_hypotheses"},
    )

    graph.add_edge("plan_remediation", "human_approval")

    # Node 7: interrupts here (unless the plan needs no approval); the
    # graph only reaches "execute" on a resumed, approved run.
    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"execute": "execute_remediation", "skip_execution": "validate"},
    )

    graph.add_edge("execute_remediation", "validate")
    graph.add_edge("validate", END)

    return graph.compile(checkpointer=MemorySaver())
