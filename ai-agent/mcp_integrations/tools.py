"""
Domain-specific async helpers built on mcp_integrations/client.py -- what
graph nodes actually import. Nodes never touch ClientSession directly;
each function here opens exactly one MCP session covering everything it
needs, so a node that wants three related tool results doesn't spawn
three separate server subprocesses.
"""
import os

from mcp_integrations.client import (
    OBSERVABILITY_SERVER,
    REMEDIATION_SERVER,
    call_tool,
    github_mcp_session,
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
            evidence["recent_deployment"] = await get_recent_deployment_evidence()

    if len(evidence) == 1:  # nothing matched -- fall back to a general snapshot
        async with mcp_session(OBSERVABILITY_SERVER) as session:
            evidence["service_metrics"] = await call_tool(session, "get_service_metrics")

    return evidence


async def get_recent_deployment_evidence(limit: int = 5) -> dict:
    """
    Deployment-hypothesis evidence (Spec Section 12 Scenario 4): the
    last `limit` commits plus the full changed-files list for the most
    recent one, via GitHub's own remote MCP server -- this is what makes
    that server "genuinely useful" per the spec rather than decorative.

    Degrades to a note instead of raising when GITHUB_TOKEN/GITHUB_REPO
    aren't configured, or if the live call fails for any reason (network,
    rate limit, revoked token) -- a missing/broken *optional* evidence
    source shouldn't crash the whole investigation graph; the LLM
    evaluating evidence just reasons with one less input, the same as a
    human investigator who couldn't reach GitHub right now.
    """
    repo = os.getenv("GITHUB_REPO")
    if not os.getenv("GITHUB_TOKEN") or not repo:
        return {"note": "GITHUB_TOKEN/GITHUB_REPO not configured -- skipping git correlation."}

    owner, name = repo.split("/", 1)
    try:
        async with github_mcp_session() as session:
            commits = await call_tool(
                session, "list_commits", {"owner": owner, "repo": name, "perPage": limit}
            )
            if not isinstance(commits, list) or not commits:
                return {"note": "no commits returned"}

            latest = commits[0]
            commit_detail = await call_tool(
                session, "get_commit", {"owner": owner, "repo": name, "sha": latest["sha"]}
            )
    except Exception as exc:  # noqa: BLE001 -- see docstring: degrade, don't crash
        return {"note": f"GitHub MCP call failed: {exc}"}

    return {
        "recent_commits": [
            {"sha": c["sha"][:12], "message": c["commit"]["message"].splitlines()[0]}
            for c in commits
        ],
        "latest_commit": {
            "sha": commit_detail.get("sha", latest["sha"])[:12],
            "message": commit_detail.get("commit", {}).get("message", "").splitlines()[0],
            "files_changed": [f["filename"] for f in commit_detail.get("files", [])],
        },
    }


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
