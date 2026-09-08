# Agentic DevOps Incident Response POC

A learning-focused POC: an AI agent (LangChain + LangGraph + MCP,
observed via LangSmith) investigates incidents in a Spring Boot service
monitored by Prometheus, and asks for human approval before taking any
remediation action.

Full design spec: [PLAN.md](PLAN.md) — read it first, it's the source of
truth for architecture and the step-by-step build sequence.
Running commentary on *why* each piece works the way it does:
[docs/learning-notes.md](docs/learning-notes.md).

## Status

- ✅ **Phase 1 — isolated fundamentals**: built and verified (this
  directory's `ai-agent/step1..4_*` scripts). See below to run them.
- ✅ **Phase 2 — Spring Boot + Prometheus infra**: `demo-service/` (Order
  Service) and `prometheus/` built and verified end-to-end — see
  "Running Phase 2" below.
- 🟡 **Phase 3 — MCP servers**: observability-server and
  remediation-server built and verified live. GitHub MCP client written
  but unverified — needs a `GITHUB_TOKEN` (see "Running Phase 3" below).
- ⬜ **Phase 4 — full LangGraph incident-response workflow**: not yet
  built.

## One-time setup

Toolchain (already done in this checkout, listed for reproducibility):

```bash
brew install openjdk maven prometheus python@3.12
```

`openjdk` is keg-only (macOS's own `/usr/bin/java` is a stub that
errors), so `mvn`/Spring Boot commands need it on `PATH` explicitly:

```bash
source scripts/env.sh   # PATH + JAVA_HOME for this shell
```

Python env for the AI agent:

```bash
cd ai-agent
python3.12 -m venv .venv        # already created in this checkout
./.venv/bin/pip install -r requirements.txt
cp .env.example .env            # already done in this checkout
```

Then edit `ai-agent/.env` and set at least `ANTHROPIC_API_KEY` — every
LLM-calling step is gated on it and prints a clear message instead of
failing if it's missing. `LANGCHAIN_API_KEY`/`LANGCHAIN_TRACING_V2` (for
LangSmith) and `GITHUB_TOKEN` (for GitHub MCP, Phase 3) are optional and
only needed once you reach the steps that use them.

## Running Phase 1

From `ai-agent/`:

```bash
.venv/bin/python step1_langchain_basics.py     # needs ANTHROPIC_API_KEY
.venv/bin/python step2_langgraph_basics.py     # no keys needed
.venv/bin/python step3_mcp_basics/client.py    # no keys needed
.venv/bin/python step4_langsmith_tracing.py    # explains tracing; runs a
                                                # traced call if LangSmith
                                                # + Anthropic keys are set
```

Each script's docstring explains what it demonstrates and the "learning
questions" it's meant to answer — see
[docs/learning-notes.md](docs/learning-notes.md) for the answers.

## Running Phase 2

Start both natively (no Docker yet — see `PLAN.md` Section 18):

```bash
scripts/start-infra.sh
```

This starts:
- **Order Service** (Spring Boot 4 / Java 26, via Maven) on `:8080` —
  `POST /orders`, `GET /orders/{id}`, `GET /orders`, plus
  `/actuator/health` and `/actuator/prometheus`.
- **Prometheus** on `:9090`, scraping the Order Service every 5s per
  `prometheus/prometheus.yml`.

Verify the full path end-to-end:

```bash
curl -X POST localhost:8080/orders -H 'Content-Type: application/json' \
  -d '{"item":"widget","quantity":3}'
curl localhost:8080/orders
curl localhost:8080/actuator/prometheus | grep http_server_requests_seconds_count

# Prometheus UI: http://localhost:9090 — Graph tab, query:
#   http_server_requests_seconds_count{application="order-service"}
# or via API:
curl --data-urlencode \
  'query=http_server_requests_seconds_count{application="order-service"}' \
  localhost:9090/api/v1/query
```

Stop both with `scripts/stop-infra.sh`.

## Running Phase 3

With Order Service + Prometheus running (`scripts/start-infra.sh`):

```bash
# Observability MCP: 5 read-only tools over Prometheus + Actuator + logs
ai-agent/.venv/bin/python mcp-servers/observability-server/test_client.py

# Remediation MCP: the one write tool. This really restarts the Order
# Service process (no approval gate at this layer — see learning-notes.md)
ai-agent/.venv/bin/python mcp-servers/remediation-server/test_client.py

# GitHub MCP: needs GITHUB_TOKEN + GITHUB_REPO in ai-agent/.env first;
# prints setup instructions and exits cleanly if unset
ai-agent/.venv/bin/python ai-agent/mcp/github_client.py
```

## Project layout

See `PLAN.md` Section 17 for the full intended layout. Directories not
yet populated (`demo-service/`, `mcp-servers/*`, `prometheus/`,
`ai-agent/graph/`, `ai-agent/nodes/`) are placeholders for Phases 2–4.
