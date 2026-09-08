"""
Node 7 (Spec Section 11): Human Approval.

This is the node the whole spec keeps pointing at (Section 22
Principle 3, Section 8's "Human Approval Required" box): the one place
where a write action is gated on a person, not the model. LangGraph's
`interrupt()` is what makes this a genuine pause-and-resume rather than
a blocking `input()` call -- it raises a `GraphInterrupt` that unwinds
execution back to the caller with a checkpoint saved (via the
checkpointer passed to `.compile()`), and the caller resumes later with
`app.invoke(Command(resume=<answer>), config)` using the *same* thread
id. main.py is what actually calls `input()`, outside the graph.

If the plan doesn't call for an action (`NONE`) or that action itself
says it doesn't need approval, there's nothing to interrupt for --
approving a no-op would be a pointless prompt.
"""
from langgraph.types import interrupt


def human_approval(state: dict) -> dict:
    plan = state.get("remediation_plan", {})

    if not plan.get("requires_human_approval") or plan.get("action") == "NONE":
        return {"human_approved": False}

    decision = interrupt(
        {
            "type": "approval_request",
            "root_cause": state.get("root_cause"),
            "confidence": state.get("confidence"),
            "remediation_plan": plan,
        }
    )
    approved = str(decision).strip().lower() in ("y", "yes", "approve", "approved", "true")
    return {"human_approved": approved}
