"""
Manual verification client for the observability MCP server (Spec
Section 19, Step 7: "Verify manually" before any agent touches it).

Spawns server.py over stdio, lists its tools, then calls each one against
the real running Order Service + Prometheus (start them first with
scripts/start-infra.sh) and prints the results.

Run:
    ai-agent/.venv/bin/python mcp-servers/observability-server/test_client.py
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_SCRIPT = Path(__file__).parent / "server.py"


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools advertised by observability-mcp:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()

            for tool_name, args in [
                ("get_application_health", {}),
                ("get_service_metrics", {}),
                ("get_latency_metrics", {}),
                ("get_error_rate", {}),
                ("get_recent_errors", {"limit": 5}),
            ]:
                result = await session.call_tool(tool_name, arguments=args)
                print(f"--- {tool_name}({args}) ---")
                for block in result.content:
                    text = getattr(block, "text", str(block))
                    try:
                        print(json.dumps(json.loads(text), indent=2))
                    except json.JSONDecodeError:
                        print(text)
                print()


if __name__ == "__main__":
    asyncio.run(main())
