"""
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
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

MCP_SERVERS_DIR = Path(__file__).parent.parent.parent / "mcp-servers"
OBSERVABILITY_SERVER = MCP_SERVERS_DIR / "observability-server" / "server.py"
REMEDIATION_SERVER = MCP_SERVERS_DIR / "remediation-server" / "server.py"


@asynccontextmanager
async def mcp_session(server_script: Path) -> AsyncIterator[ClientSession]:
    """Spawn `server_script` over stdio and yield an initialized session."""
    params = StdioServerParameters(command=sys.executable, args=[str(server_script)])
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def call_tool(session: ClientSession, name: str, arguments: dict | None = None) -> dict:
    """Call a tool and parse its (single, text) content block as JSON."""
    result = await session.call_tool(name, arguments=arguments or {})
    if not result.content:
        return {}
    text = getattr(result.content[0], "text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
