"""
Node 2 (Spec Section 11): Gather Initial Evidence.

Deliberately deterministic, no LLM call -- Spec Section 22 Principle 1:
"Use deterministic code when the operation is deterministic." There is
no judgment involved in deciding to check health/metrics/errors at the
start of every investigation; it's always useful, so it's plain code
calling MCP tools, not a model deciding whether to bother.
"""
import asyncio

from mcp_integrations.tools import gather_initial_evidence


def gather_evidence(state: dict) -> dict:
    return asyncio.run(gather_initial_evidence())
