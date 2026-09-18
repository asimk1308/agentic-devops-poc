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

Defense-in-depth guard: the graph topology (routes.route_after_approval)
is the only thing that's supposed to keep this node from running without
approval. That's correct today, but nothing at this node itself stops a
future edge/rewiring bug from reaching it unapproved -- and this is the
one write action in the whole POC (mcp-servers/remediation-server/server.py
itself performs no approval check either). So check `human_approved`
here too, even though it's redundant with routing, as of now.
"""
import asyncio

from mcp_integrations.tools import execute_restart_service


def execute_remediation(state: dict) -> dict:
    if not state.get("human_approved"):
        return {
            "execution_result": {
                "action": "restart_service",
                "result": "BLOCKED",
                "reason": "execute_remediation reached without human_approved=True",
            }
        }
    return {"execution_result": asyncio.run(execute_restart_service())}
