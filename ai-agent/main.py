"""
Phase 4 entry point: run the full incident-response graph end to end
(Spec Section 25's 18-step demo).

Usage:
    ai-agent/.venv/bin/python ai-agent/main.py "Investigate performance
        degradation in Order Service."

With no argument, uses the spec's own example incident description.

Requires ANTHROPIC_API_KEY (nodes 1, 3, 5, 6 call the LLM) and the
Order Service + Prometheus running (scripts/start-infra.sh) so the MCP
tool calls in nodes 2/4/8/9 have something real to read.

This script is the *only* place that calls `input()` -- the graph
itself never blocks on stdin. nodes/human_approval.py's `interrupt()`
unwinds execution back here with the state saved (Section 8's "Human
Approval Required" pause); this loop notices the pause via the
`__interrupt__` key `.invoke()` returns, prints the recommendation, asks
the human, then resumes the *same* thread with `Command(resume=...)`.
"""
import os
import sys
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from graph.graph import build_graph  # noqa: E402  (after load_dotenv, before use)

DEFAULT_INCIDENT = "Investigate performance degradation in Order Service."


def _print_approval_request(payload: dict) -> None:
    plan = payload.get("remediation_plan", {})
    print("\n" + "=" * 60)
    print("HUMAN APPROVAL REQUIRED")
    print("=" * 60)
    print(f"Root cause:  {payload.get('root_cause')}")
    print(f"Confidence:  {payload.get('confidence', 0.0):.0%}")
    print(f"Action:      {plan.get('action')}")
    print(f"Reason:      {plan.get('reason')}")
    print(f"Risk:        {plan.get('risk')}")
    print("=" * 60)


def run(incident_description: str) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set in ai-agent/.env -- every LLM node "
              "in this graph needs it. See README.md 'One-time setup'.")
        return

    app = build_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    incident_id = config["configurable"]["thread_id"]

    print(f"Incident {incident_id}: {incident_description}\n")

    result = app.invoke(
        {"incident_id": incident_id, "incident_description": incident_description},
        config=config,
    )

    while "__interrupt__" in result:
        interrupt = result["__interrupt__"][0]
        _print_approval_request(interrupt.value)
        answer = input("Approve? [y/N]: ")
        result = app.invoke(Command(resume=answer), config=config)

    print("\n" + "-" * 60)
    print(result.get("final_summary", "(no final summary produced)"))
    print("-" * 60)


if __name__ == "__main__":
    description = " ".join(sys.argv[1:]) or DEFAULT_INCIDENT
    run(description)
