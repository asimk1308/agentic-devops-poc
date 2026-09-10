"""
🧒 For a kid: Step 8. Only happens if you said yes in Step 7. This is
the one spot in the whole detective story where she actually DOES
something for real -- pressing the button to restart the service --
instead of just looking and thinking.

Node 8 (Spec Section 11): Execute Remediation.

Only reachable when routes.route_after_approval sends the graph here --
i.e. `human_approved` is True. Calls the one action tool the remediation
MCP server exposes; which tool to call isn't a branch here because this
POC only ever plans `RESTART_SERVICE` (nodes/remediation.py's prompt is
constrained to that same one action, see Section 7 MCP Server 3).
"""
import asyncio

from mcp_integrations.tools import execute_restart_service


def execute_remediation(state: dict) -> dict:
    return {"execution_result": asyncio.run(execute_restart_service())}
