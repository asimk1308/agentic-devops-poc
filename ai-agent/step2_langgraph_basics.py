"""
Step 2 — LangGraph basics.

Goal: understand graph execution — nodes, edges, conditional routing, and
shared state — completely independent of any LLM or MCP call. The
"healthy?" decision below is a plain threshold check on purpose: this
isolates what LangGraph itself adds versus what an LLM would add later.

  START -> analyze -> [conditional] -> investigate -> END
                                     -> healthy     -> END

Run:
    ai-agent/.venv/bin/python ai-agent/step2_langgraph_basics.py

Learning questions to answer for yourself after running this (see
docs/learning-notes.md):
  - What is a node? (a function that takes state, returns a partial
    state update)
  - What is an edge? (a fixed transition between two nodes)
  - What is conditional routing? (a function that inspects state and
    returns which edge to take next)
  - What is graph state? (the shared TypedDict every node reads from and
    writes back into — NOT the same as LLM conversation memory; see
    Step 10+ / docs/learning-notes.md for that distinction)
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class TriageState(TypedDict):
    latency_ms: int
    status: str
    notes: list[str]


def analyze(state: TriageState) -> dict:
    notes = state.get("notes", [])
    notes = notes + [f"Observed latency: {state['latency_ms']}ms"]
    return {"notes": notes}


def investigate(state: TriageState) -> dict:
    notes = state.get("notes", []) + ["Latency above threshold — flagging for investigation."]
    return {"status": "INVESTIGATING", "notes": notes}


def mark_healthy(state: TriageState) -> dict:
    notes = state.get("notes", []) + ["Latency within normal range."]
    return {"status": "HEALTHY", "notes": notes}


def route_after_analyze(state: TriageState) -> str:
    """Conditional edge: deterministic routing, no LLM involved."""
    return "investigate" if state["latency_ms"] > 500 else "healthy"


def build_graph():
    graph = StateGraph(TriageState)
    graph.add_node("analyze", analyze)
    graph.add_node("investigate", investigate)
    graph.add_node("healthy", mark_healthy)

    graph.add_edge(START, "analyze")
    graph.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"investigate": "investigate", "healthy": "healthy"},
    )
    graph.add_edge("investigate", END)
    graph.add_edge("healthy", END)

    return graph.compile()


def run(app, latency_ms: int) -> None:
    result = app.invoke({"latency_ms": latency_ms, "status": "", "notes": []})
    print(f"\n--- latency_ms={latency_ms} ---")
    print("status:", result["status"])
    for note in result["notes"]:
        print(" -", note)


if __name__ == "__main__":
    app = build_graph()
    run(app, 120)   # takes the "healthy" edge
    run(app, 3000)  # takes the "investigate" edge
