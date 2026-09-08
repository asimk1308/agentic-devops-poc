"""
Domain-specific async helpers built on mcp_integrations/client.py -- what
graph nodes actually import. Nodes never touch ClientSession directly;
each function here opens exactly one MCP session covering everything it
needs, so a node that wants three related tool results doesn't spawn
three separate server subprocesses.
"""
from mcp_integrations.client import (
    OBSERVABILITY_SERVER,
    REMEDIATION_SERVER,
    call_tool,
    mcp_session,
)


async def gather_initial_evidence() -> dict:
    """Node 2 (Spec Section 11): health + metrics + recent errors, one call each."""
    async with mcp_session(OBSERVABILITY_SERVER) as session:
        health = await call_tool(session, "get_application_health")
        metrics = await call_tool(session, "get_service_metrics")
        errors = await call_tool(session, "get_recent_errors", {"limit": 10})
    return {"health_status": health, "metrics": metrics, "logs": errors}


async def investigate_hypothesis(hypothesis_description: str) -> dict:
    """
    Node 4 (Spec Section 11): pull the evidence relevant to one specific
    hypothesis, keyed off keywords in its description -- e.g. a "database
    connection pool" hypothesis pulls recent error logs; a "resource
    exhaustion" hypothesis re-checks metrics. Deterministic dispatch, not
    an LLM decision (Spec Section 22 Principle 1: use plain code where the
    routing itself doesn't require judgment).
    """
    text = hypothesis_description.lower()
    evidence: dict = {"hypothesis": hypothesis_description}

    async with mcp_session(OBSERVABILITY_SERVER) as session:
        if any(kw in text for kw in ("database", "connection", "timeout", "error")):
            evidence["recent_errors"] = await call_tool(session, "get_recent_errors", {"limit": 15})
        if any(kw in text for kw in ("resource", "memory", "cpu", "exhaustion")):
            evidence["latency_metrics"] = await call_tool(session, "get_latency_metrics")
        if any(kw in text for kw in ("deployment", "regression", "release", "code change")):
            evidence["health"] = await call_tool(session, "get_application_health")
            evidence["git_note"] = (
                "GitHub MCP not queried here -- see "
                "mcp_integrations/github_client.py; needs GITHUB_TOKEN/GITHUB_REPO."
            )

    if len(evidence) == 1:  # nothing matched -- fall back to a general snapshot
        async with mcp_session(OBSERVABILITY_SERVER) as session:
            evidence["service_metrics"] = await call_tool(session, "get_service_metrics")

    return evidence


async def execute_restart_service() -> dict:
    """Node 8 (Spec Section 11): the one remediation action this POC has."""
    async with mcp_session(REMEDIATION_SERVER) as session:
        return await call_tool(session, "restart_service")


async def get_validation_snapshot() -> dict:
    """Node 9 (Spec Section 11): post-remediation health + metrics, to diff against the pre-action snapshot."""
    async with mcp_session(OBSERVABILITY_SERVER) as session:
        health = await call_tool(session, "get_application_health")
        metrics = await call_tool(session, "get_service_metrics")
    return {"health_status": health, "metrics": metrics}
