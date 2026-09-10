"""
🧒 For a kid: these are the two "which way do we go?" signs on the map
in graph.py. They don't think or guess anything themselves -- they just
look at a number or a yes/no the detective already wrote down, and point
left or right. Simple, boring, and exactly why nothing goes wrong here.

Conditional edges (Spec Section 11 Step 13, Section 8's diamond
decision points). Each function only inspects state and returns a
string key -- no LLM calls here; *deciding how to route* on numbers
already produced by an LLM node is exactly the kind of deterministic
logic Section 22 Principle 1 asks for.
"""

CONFIDENCE_THRESHOLD = 0.7
MAX_INVESTIGATION_LOOPS = 2


def route_after_evaluate(state: dict) -> str:
    """
    Step 13's investigation loop: if the evidence gathered so far isn't
    conclusive, go generate a fresh round of hypotheses against the
    now-larger evidence pile and investigate again, instead of forcing a
    root-cause call on weak evidence. Capped by MAX_INVESTIGATION_LOOPS
    so a stubbornly ambiguous incident still terminates.
    """
    confidence = state.get("confidence", 0.0)
    loops = state.get("investigation_loops", 0)

    if confidence >= CONFIDENCE_THRESHOLD or loops >= MAX_INVESTIGATION_LOOPS:
        return "remediation"
    return "investigate_more"


def route_after_approval(state: dict) -> str:
    """
    Section 8's post-approval diamond: APPROVE -> execute, REJECT (or no
    approval needed / plan was NONE) -> skip straight to validate, which
    reports the current state without a before/after diff.
    """
    return "execute" if state.get("human_approved") else "skip_execution"
