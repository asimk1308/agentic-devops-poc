"""
🧒 For a kid: this file is a walkie-talkie. It knows how to call up a
helper, say "hey, do this one job for me," and bring back the answer.
There are two kinds of walkie-talkies here: `mcp_session` calls a helper
running right on this same computer, and `github_mcp_session` calls a
helper far away on the internet (GitHub) -- same walkie-talkie buttons
either way, just a different phone line underneath.

Generic MCP stdio client helper.

(Note on location: the spec's project structure calls this directory
`ai-agent/mcp/` -- that name was tried first and doesn't work: a
directory literally named `mcp` sitting next to a script that becomes
sys.path[0] makes the *installed* `mcp` SDK package win over anything of
ours, so `from mcp import tools` (our own tools.py) fails outright with
"cannot import name 'tools' from 'mcp'" -- confirmed empirically before
renaming to `mcp_integrations`. See docs/learning-notes.md Phase 4 for
the reproduction.)

Wraps the connect/initialize/call_tool dance every test_client.py in
mcp-servers/*/ hand-rolled (Steps 3/7/9) into one reusable async context
manager, since graph nodes call MCP tools repeatedly rather than as
one-off manual verification scripts.
"""
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import httpx2
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

MCP_SERVERS_DIR = Path(__file__).parent.parent.parent / "mcp-servers"
OBSERVABILITY_SERVER = MCP_SERVERS_DIR / "observability-server" / "server.py"
REMEDIATION_SERVER = MCP_SERVERS_DIR / "remediation-server" / "server.py"

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


@asynccontextmanager
async def mcp_session(server_script: Path) -> AsyncIterator[ClientSession]:
    """Spawn `server_script` over stdio and yield an initialized session."""
    params = StdioServerParameters(command=sys.executable, args=[str(server_script)])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


@asynccontextmanager
async def github_mcp_session() -> AsyncIterator[ClientSession]:
    """
    Same shape as mcp_session(), but for GitHub's own remote MCP server
    (Section 7 MCP Server 1) -- streamable-HTTP + bearer auth instead of
    a locally-spawned stdio subprocess, since this is a server GitHub
    operates, not one this repo hosts. See github_client.py for the
    tool-discovery script this was first verified with. Raises
    RuntimeError if GITHUB_TOKEN isn't set -- callers (tools.py) catch
    this to degrade gracefully rather than crash an investigation.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"})
    async with streamable_http_client(GITHUB_MCP_URL, http_client=http_client) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def call_tool(session: ClientSession, name: str, arguments: dict | None = None) -> Any:
    """Call a tool and parse its (single, text) content block as JSON -- a dict for most
    tools, but e.g. GitHub's `list_commits` returns a JSON list, hence `Any` not `dict`."""
    result = await session.call_tool(name, arguments=arguments or {})
    if not result.content:
        return {}
    text = getattr(result.content[0], "text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
