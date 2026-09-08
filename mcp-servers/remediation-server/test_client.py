"""
Manual verification client for the remediation MCP server (Spec Section
19, Step 9: build the one action tool, "test manually," do NOT wire it
into the agent yet).

Calls restart_service() directly -- there is no human-approval gate at
this layer on purpose (see server.py's docstring); that gate is a
LangGraph node built in Phase 4. Confirms the Order Service actually goes
down and back up, using get_application_health()-equivalent Actuator
polling before/after.

Run:
    ai-agent/.venv/bin/python mcp-servers/remediation-server/test_client.py
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_SCRIPT = Path(__file__).parent / "server.py"
ORDER_SERVICE_HEALTH_URL = "http://localhost:8080/actuator/health"


def _health() -> str:
    try:
        resp = httpx.get(ORDER_SERVICE_HEALTH_URL, timeout=2.0)
        return resp.json().get("status", "UNKNOWN")
    except httpx.HTTPError:
        return "UNREACHABLE"


async def main() -> None:
    print("Order Service health before restart:", _health())

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("\nTools advertised by remediation-mcp:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description.strip().splitlines()[0]}")

            print("\nCalling restart_service() ...")
            result = await session.call_tool("restart_service", arguments={})
            for block in result.content:
                text = getattr(block, "text", str(block))
                print(json.dumps(json.loads(text), indent=2))

    print("\nOrder Service health after restart:", _health())


if __name__ == "__main__":
    asyncio.run(main())
