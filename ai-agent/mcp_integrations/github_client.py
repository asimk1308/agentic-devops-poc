"""
GitHub MCP connection (Spec Section 7, MCP Server 1 — Source Control).

Spec: "For the POC, use an existing GitHub MCP server if possible" and
"Learning objective: understand how an agent discovers and calls tools
exposed by an EXTERNAL MCP server" -- i.e. this is deliberately not a
server we host ourselves, unlike observability-server/remediation-server.
It connects to GitHub's own remote MCP server over streamable-HTTP,
authenticated with a personal access token, instead of spawning a local
subprocess over stdio like Steps 3/7/9 did. Same ClientSession API
either way -- only the transport changes, which is the point of MCP
being a client/server *protocol* rather than a library you import.

STATUS: not yet verified live -- no GITHUB_TOKEN is configured (see
ai-agent/.env.example). This script deliberately does NOT hardcode which
tool names GitHub's server exposes (e.g. "list_commits" vs
"list_recent_commits") because that surface can change; instead it lists
whatever tools the server advertises and searches for ones that look
like commit/file-history tools, then calls the best match. Run it once a
token is set to confirm the actual names and fill in
docs/learning-notes.md's Phase 3 Step 8 section with what came back.

Setup:
  1. Create a GitHub personal access token (fine-grained, "Contents:
     read-only" on the repo you want to correlate deployments against;
     classic PAT with "repo" scope also works).
  2. In ai-agent/.env, set GITHUB_TOKEN=<token> and
     GITHUB_REPO=<owner>/<repo>.

Run:
    ai-agent/.venv/bin/python ai-agent/mcp/github_client.py
"""
import asyncio
import os
from pathlib import Path

import httpx2
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv(Path(__file__).parent.parent / ".env")

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # "owner/repo"

# Tool-name substrings we'd consider a match for "recent commits" /
# "changed files", since the exact advertised names aren't hardcoded.
COMMIT_TOOL_HINTS = ("list_commit", "recent_commit", "commits")
FILES_TOOL_HINTS = ("changed_file", "diff", "compare")


def _pick_tool(tools, hints) -> str | None:
    for tool in tools:
        name = tool.name.lower()
        if any(hint in name for hint in hints):
            return tool.name
    return None


async def main() -> None:
    if not GITHUB_TOKEN:
        print(
            "GITHUB_TOKEN is not set in ai-agent/.env -- nothing to verify yet.\n"
            "This is expected/optional at this stage of the POC.\n\n"
            "What this script will do once a token is set:\n"
            "  1. Connect to GitHub's remote MCP server over streamable-HTTP\n"
            "     (Bearer-token authenticated) instead of spawning a local\n"
            "     stdio subprocess -- same ClientSession API as Steps 3/7/9,\n"
            "     different transport.\n"
            "  2. session.list_tools() -- print every tool GitHub's server\n"
            "     advertises (this alone answers the Step 8 learning\n"
            "     objective: discovering tools on an EXTERNAL MCP server\n"
            "     you don't control).\n"
            "  3. Find and call a commit-listing tool for GITHUB_REPO, and a\n"
            "     changed-files/diff tool for the most recent commit -- the\n"
            "     two calls Phase 4's investigation node needs for\n"
            "     deployment-regression correlation (Spec Section 12,\n"
            "     Scenario 4)."
        )
        return

    if not GITHUB_REPO:
        print("GITHUB_TOKEN is set but GITHUB_REPO is not (expected 'owner/repo'). Set it and re-run.")
        return

    owner, repo = GITHUB_REPO.split("/", 1)
    http_client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {GITHUB_TOKEN}"})

    async with streamable_http_client(GITHUB_MCP_URL, http_client=http_client) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print(f"Tools advertised by GitHub's MCP server ({len(tools)} total):")
            for tool in tools:
                print(f"  - {tool.name}")

            commit_tool = _pick_tool(tools, COMMIT_TOOL_HINTS)
            if commit_tool:
                print(f"\nCalling '{commit_tool}' for {GITHUB_REPO} ...")
                result = await session.call_tool(
                    commit_tool, arguments={"owner": owner, "repo": repo}
                )
                for block in result.content:
                    print(getattr(block, "text", block))
            else:
                print("\nNo obvious commit-listing tool found by name match --"
                      " inspect the tool list above and update COMMIT_TOOL_HINTS.")


if __name__ == "__main__":
    asyncio.run(main())
