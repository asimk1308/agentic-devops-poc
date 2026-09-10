# Agentic DevOps Incident Response POC

A learning-focused POC: an AI agent (LangChain + LangGraph + MCP,
observed via LangSmith) investigates incidents in a Spring Boot service
monitored by Prometheus, and asks for human approval before taking any
remediation action.

Full design spec: [PLAN.md](PLAN.md) — read it first, it's the source of
truth for architecture and the step-by-step build sequence.
[docs/architecture.md](docs/architecture.md) is the as-built picture
(what's real right now vs. still spec-shaped). Running commentary on
*why* each piece works the way it does:
[docs/learning-notes.md](docs/learning-notes.md). Live-demo walkthroughs:
[docs/demo-script.md](docs/demo-script.md).

## Status

- ✅ **Phase 1 — isolated fundamentals**: built and verified (this
  directory's `ai-agent/step1..4_*` scripts). See below to run them.
- ✅ **Phase 2 — Spring Boot + Prometheus infra**: `demo-service/` (Order
  Service) and `prometheus/` built and verified end-to-end — see
  "Running Phase 2" below.
- ✅ **Phase 3 — MCP servers**: observability-server, remediation-server,
  and GitHub MCP all built and verified live (see "Running Phase 3").
- ✅ **Phase 4 — full LangGraph incident-response workflow**: built,
  wired, and verified live end-to-end — all 9 nodes, the Step 13
  investigation loop, the Node 7 human-approval interrupt (both approve
  and reject paths), all three Section 21 demo scenarios including
  Scenario 4's GitHub-commit correlation, real LLM calls throughout.
  Currently running on a local model (Ollama + `qwen2.5`,
  `LLM_PROVIDER=ollama`) rather than Anthropic — see "Running Phase 4"
  below and `docs/learning-notes.md` for why and what it surfaced.
- ✅ **Fault injection (Section 12)**: latency and error-rate injection
  (`scripts/inject_latency.sh` / `inject_failure.sh`) built and verified
  live end-to-end through Prometheus into the observability MCP tools —
  see "Running fault injection" and `docs/demo-script.md`.
- ✅ **LangSmith tracing (Section 16)**: verified live — confirmed via
  the LangSmith API directly, not just a clean exit, that a full graph
  run produces one traced run per node/route plus the full
  prompt→model→parser chain underneath each LLM node. See
  `docs/learning-notes.md` for a real gap it surfaced (MCP tool calls
  aren't visible inside the trace, only the node that made them).

All 18 steps of `PLAN.md` Section 25's "Definition of Success" checklist
are now verified live at least once.

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

# Optional, only if your editor runs mypy (VS Code's Mypy Type Checker
# extension, etc.) and you want it actually checking this code instead
# of erroring on every first-party import:
./.venv/bin/pip install -r requirements-dev.txt
```

Then edit `ai-agent/.env` and set `LLM_PROVIDER` (see `ai-agent/llm.py`):
- `anthropic` (default): set `ANTHROPIC_API_KEY` too — needs a
  workspace-scoped key with a funded workspace (an org-level key without
  a workspace, or one with a $0 balance, fails at request time with a
  clear error either way).
- `ollama`: no key needed, but `ollama serve` must be running locally
  with `OLLAMA_MODEL` (default `qwen2.5`) pulled — `ollama pull qwen2.5`
  if you don't have it. This is what's actually configured and verified
  in this checkout (see `docs/learning-notes.md` for why, and a real
  structured-output gap it surfaced with a local model).

`GITHUB_TOKEN` + `GITHUB_REPO` (for GitHub MCP, Phase 3, and Scenario
4's deployment correlation) and `LANGCHAIN_API_KEY` +
`LANGCHAIN_TRACING_V2=true` (for LangSmith tracing) are optional and
only needed once you reach the steps that use them — all are set in
this checkout (see "Status" above).

## Running Phase 1

From `ai-agent/`:

```bash
.venv/bin/python step1_langchain_basics.py     # needs an LLM (llm.py)
.venv/bin/python step2_langgraph_basics.py     # no keys needed
.venv/bin/python step3_mcp_basics/client.py    # no keys needed
.venv/bin/python step4_langsmith_tracing.py    # explains tracing; runs a
                                                # traced call if LangSmith
                                                # is configured too
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
# lists all tools GitHub's server advertises, then lists recent commits
ai-agent/.venv/bin/python ai-agent/mcp_integrations/github_client.py
```

## Running Phase 4

With Order Service + Prometheus running (`scripts/start-infra.sh`) and
an LLM configured (`ai-agent/.env` — see "One-time setup" above):

```bash
ai-agent/.venv/bin/python ai-agent/main.py "Investigate performance degradation in Order Service."
# or, with no argument, uses that same sentence as the default incident
ai-agent/.venv/bin/python ai-agent/main.py
```

This runs the full Section 8 graph: understand → gather evidence →
generate hypotheses → investigate → evaluate (looping back through
generate/investigate up to twice if confidence stays below 70%) →
plan remediation → **pause for your y/n approval in the terminal** → (if
approved) execute the restart → validate → print a before/after
summary. Nothing is executed without that approval prompt — approve
only if you actually want the real Order Service process restarted.

To watch the full trace (every node, every conditional route, every LLM
call's exact prompt/response) in LangSmith instead of only the terminal
output, set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` in
`ai-agent/.env` first (Spec Section 16) — already on in this checkout.
Note MCP tool calls themselves don't show up as separate trace entries
(see `docs/learning-notes.md`).

For an incident description that steers toward the deployment-regression
hypothesis (Scenario 4, pulls real commit data via GitHub MCP — needs
`GITHUB_TOKEN`/`GITHUB_REPO`, and a `git push` first so the agent sees
your actual latest commit), see `docs/demo-script.md` Scenario 3.

## Running fault injection

With Order Service + Prometheus running (`scripts/start-infra.sh`):

```bash
scripts/inject_latency.sh 2000     # Scenario 2 — restarts with a 2s
                                    # injected delay on every request
scripts/inject_failure.sh 0.3      # Scenario 3 — restarts with 30% of
                                    # requests returning a real 5xx

python3 scripts/generate_load.py --duration 20 --rate 5   # generate
                                    # real traffic so Prometheus's
                                    # rate()-based queries move

scripts/clear_faults.sh            # reset to a clean, no-fault state
```

See [docs/demo-script.md](docs/demo-script.md) for full scenario
walkthroughs combining this with `ai-agent/main.py`.

## Project layout

See `PLAN.md` Section 17 for the full intended layout.
`ai-agent/graph/`, `ai-agent/nodes/`, `ai-agent/mcp_integrations/`, and
`ai-agent/prompts/` (Phase 4) are now populated; `demo-service/`,
`mcp-servers/*`, and `prometheus/` (Phases 2–3) already were.
