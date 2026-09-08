"""
Node 4 (Spec Section 11): Investigation Loop.

Pulls hypothesis-specific evidence for whichever hypotheses haven't been
investigated yet, then appends to `investigation_results` and bumps
`investigation_loops`. Deterministic dispatch again (Section 22
Principle 1) -- deciding *what* to fetch for a given hypothesis is
keyword-based in mcp_integrations.tools.investigate_hypothesis, not an
LLM call; the LLM's job is Node 5 (evaluating what came back), not
Node 4 (fetching it).

Why does this run every hypothesis in one pass instead of one node
execution per hypothesis? Section 11's "Investigation Loop" is about
looping the gather -> evaluate cycle (route_after_evaluate in
graph/routes.py) when confidence is still too low after a pass -- not
about looping per-hypothesis within a single pass. One pass already
covers every hypothesis generated so far; a second pass only happens if
evaluate_evidence decides confidence is insufficient, at which point
generate_hypotheses/investigate run again against the accumulated
evidence.
"""
import asyncio

from mcp_integrations.tools import investigate_hypothesis


def investigate(state: dict) -> dict:
    hypotheses = state.get("hypotheses", [])
    prior_results = state.get("investigation_results", [])
    already_investigated = {r["hypothesis"] for r in prior_results}

    new_results = [
        asyncio.run(investigate_hypothesis(h["description"]))
        for h in hypotheses
        if h["description"] not in already_investigated
    ]

    return {
        "investigation_results": prior_results + new_results,
        "investigation_loops": state.get("investigation_loops", 0) + 1,
    }
