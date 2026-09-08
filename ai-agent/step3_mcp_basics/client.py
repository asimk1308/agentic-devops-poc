"""
Step 3 — MCP basics: client.

Spawns server.py as a subprocess, speaks MCP over stdio to it, lists the
tools it advertises (tool discovery), then calls the one tool it has
(argument passing + result shape).

Run:
    ai-agent/.venv/bin/python ai-agent/step3_mcp_basics/client.py

Learning questions to answer for yourself after running this (see
docs/learning-notes.md):
  - How are tools advertised? (session.list_tools() — the server describes
    its own tools; the client doesn't hardcode knowledge of them)
  - How does the client discover tools? (initialize() handshake, then
    list_tools())
  - How are arguments passed? (call_tool(name, arguments=dict) — a plain
    JSON-serializable dict, validated against the tool's schema)
  - How are results returned? (a list of content blocks — text here, but
    could be images/resources)
  - What transport is being used? (stdio: the client owns the server's
    process lifecycle; contrast with an HTTP-based MCP server you'd
    instead point a URL at)
"""
import asyncio
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
            print("Tools advertised by the server:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            result = await session.call_tool("get_current_time", arguments={})
            print("\nResult of calling get_current_time():")
            for block in result.content:
                print(" ", getattr(block, "text", block))


if __name__ == "__main__":
    asyncio.run(main())
