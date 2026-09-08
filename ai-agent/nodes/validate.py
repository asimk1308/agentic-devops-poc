"""
Node 9 (Spec Section 11): Validate.

Re-pulls health + metrics after remediation and diffs them against the
snapshot gather_evidence() took at the very start of the investigation,
producing the plain-English before/after summary the spec's Section 11
example shows. This node also runs when no action was taken (skipped
approval or NONE plan) -- there's nothing to validate against a prior
snapshot in that case, so it reports the current state instead of a
diff.
"""
import asyncio

from mcp_integrations.tools import get_validation_snapshot


def validate(state: dict) -> dict:
    after = asyncio.run(get_validation_snapshot())

    if not state.get("execution_result"):
        summary = (
            f"No remediation action executed. Root cause: "
            f"{state.get('root_cause', 'unknown')} "
            f"(confidence {state.get('confidence', 0.0):.0%}). "
            f"Current status: {after.get('health_status', {}).get('status', 'UNKNOWN')}."
        )
        return {"validation": {"after": after}, "final_summary": summary}

    before_health = state.get("health_status", {})
    before_metrics = state.get("metrics", {})
    after_health = after.get("health_status", {})
    after_metrics = after.get("metrics", {})

    recovered = (
        after_health.get("status") == "UP"
        and after_metrics.get("status") != "DEGRADED"
    )

    summary = (
        f"INCIDENT {'RESOLVED' if recovered else 'STILL DEGRADED'}\n"
        f"Root cause: {state.get('root_cause', 'unknown')}\n"
        f"Action: {state.get('remediation_plan', {}).get('action', 'NONE')}\n"
        f"Before: health={before_health.get('status')}, "
        f"error_rate={before_metrics.get('error_rate')}, "
        f"p95_latency_ms={before_metrics.get('p95_latency_ms')}\n"
        f"After:  health={after_health.get('status')}, "
        f"error_rate={after_metrics.get('error_rate')}, "
        f"p95_latency_ms={after_metrics.get('p95_latency_ms')}"
    )

    return {
        "validation": {
            "before": {"health_status": before_health, "metrics": before_metrics},
            "after": after,
            "recovered": recovered,
        },
        "final_summary": summary,
    }
