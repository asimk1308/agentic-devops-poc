"""
Step 3 — MCP basics: server.

A throwaway MCP server exposing exactly one tool: get_current_time().

You would not normally run this file directly — client.py in this same
directory spawns it as a subprocess and talks to it over stdio, which is
the point of this example: the simplest MCP transport is "my client
launches a program and speaks a JSON-RPC-based protocol to it over
stdin/stdout." (MCP also supports SSE and streamable-HTTP transports for
servers that run independently, e.g. GitHub's or a remote observability
MCP server — Step 8 uses one of those instead of stdio.)
"""
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

server = MCPServer("mcp-basics-demo")


@server.tool()
def get_current_time() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    server.run()  # transport="stdio" by default
