"""
Opt-in integration test for the remediation MCP server's one write
action. This genuinely kills and restarts the real Order Service
process, same as manually running mcp-servers/remediation-server/test_client.py
-- only run this with `pytest -m integration` when scripts/start-infra.sh
is up and a real restart is intended; it is never part of the default
`pytest` run (see pytest.ini's addopts).
"""
import httpx
import pytest

from mcp_integrations.client import REMEDIATION_SERVER, call_tool, mcp_session

pytestmark = pytest.mark.integration


async def test_restart_service_brings_order_service_back_healthy():
    async with mcp_session(REMEDIATION_SERVER) as session:
        result = await call_tool(session, "restart_service")

    assert result["result"] == "SUCCESS"

    resp = httpx.get("http://localhost:8080/actuator/health", timeout=5.0)
    assert resp.json()["status"] == "UP"
