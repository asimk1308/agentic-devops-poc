"""
Remediation MCP server (Spec Section 7, MCP Server 3).

Exposes exactly one action tool, per Spec Section 19 Step 9: "Implement
only one action initially." Chose restart_service() over rollback_version()
because this POC has no Docker/versioned images yet (Section 18 — Docker
is deferred) — restarting the real local Order Service process is
something we can genuinely execute and verify, not simulate.

Safety rule (Spec Section 22, Principle 3): read tools (observability
server) are safe to call autonomously; this is a WRITE tool. This server
does not itself gate on human approval — that gate belongs in the
LangGraph human-approval node (Phase 4). Per Section 19 Step 9: "Do not
connect it to the agent automatically yet. Test manually" — which is
exactly what test_client.py in this directory does.

Run manually to verify (requires the Order Service running via
scripts/start-infra.sh):
    ai-agent/.venv/bin/python mcp-servers/remediation-server/test_client.py
"""
import os
import subprocess
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEMO_SERVICE_DIR = PROJECT_ROOT / "demo-service"

load_dotenv(PROJECT_ROOT / "ai-agent" / ".env")

ORDER_SERVICE_BASE_URL = os.getenv("ORDER_SERVICE_BASE_URL", "http://localhost:8080")
ORDER_SERVICE_PORT = 8080
ORDER_SERVICE_LOG_PATH = os.getenv("ORDER_SERVICE_LOG_PATH", "/tmp/order-service.log")

# openjdk is keg-only on Homebrew (see scripts/env.sh) -- Maven needs it
# on PATH/JAVA_HOME explicitly since this server doesn't inherit a shell
# that already sourced that script.
OPENJDK_BIN = "/opt/homebrew/opt/openjdk/bin"
JAVA_HOME = "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"

server = MCPServer("remediation-mcp")


def _java_env() -> dict:
    env = os.environ.copy()
    env["PATH"] = f"{OPENJDK_BIN}:{env.get('PATH', '')}"
    env["JAVA_HOME"] = JAVA_HOME
    return env


def _pid_on_port(port: int) -> int | None:
    result = subprocess.run(
        ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    pid_str = result.stdout.strip().splitlines()
    return int(pid_str[0]) if pid_str else None


def _wait_until(predicate, timeout: float, interval: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def _is_healthy() -> bool:
    try:
        resp = httpx.get(f"{ORDER_SERVICE_BASE_URL}/actuator/health", timeout=2.0)
        return resp.status_code == 200 and resp.json().get("status") == "UP"
    except httpx.HTTPError:
        return False


@server.tool()
def restart_service() -> dict:
    """
    ACTION (write) tool. Kills the Order Service process on :8080 and
    starts a fresh one via `mvn spring-boot:run`, then waits for
    /actuator/health to report UP again. Requires human approval before
    being called in the full agent workflow (Phase 4) -- not enforced by
    this server itself.
    """
    started_at = time.time()

    pid = _pid_on_port(ORDER_SERVICE_PORT)
    if pid is None:
        return {
            "action": "restart_service",
            "result": "FAILED",
            "reason": f"order-service was not running on :{ORDER_SERVICE_PORT}",
        }

    subprocess.run(["kill", str(pid)])
    port_freed = _wait_until(lambda: _pid_on_port(ORDER_SERVICE_PORT) is None, timeout=15)
    if not port_freed:
        return {
            "action": "restart_service",
            "result": "FAILED",
            "reason": f"pid {pid} did not exit within 15s",
        }

    with open(ORDER_SERVICE_LOG_PATH, "a") as log_file:
        subprocess.Popen(
            ["mvn", "-q", "spring-boot:run"],
            cwd=str(DEMO_SERVICE_DIR),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=_java_env(),
            start_new_session=True,  # survives after this MCP server process exits
        )

    healthy = _wait_until(_is_healthy, timeout=60)
    duration = round(time.time() - started_at, 1)

    return {
        "action": "restart_service",
        "result": "SUCCESS" if healthy else "TIMED_OUT",
        "previous_pid": pid,
        "duration_seconds": duration,
    }


if __name__ == "__main__":
    server.run()  # stdio transport
