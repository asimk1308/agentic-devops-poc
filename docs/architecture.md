# Architecture — what's actually built

`PLAN.md` is the design spec and source of truth for *why* each piece
exists. This document is the as-built picture: what's real in this
checkout right now, and where it still just matches the spec's target
shape. See `docs/learning-notes.md` for the running commentary on
tradeoffs, and `README.md` "Status" for the current per-phase state.

```text
                              USER
                                │
                                │ incident description (CLI arg)
                                ▼
                    ┌──────────────────────┐
                    │   ai-agent/main.py    │
                    └──────────┬───────────┘
                               │ .invoke() / Command(resume=...)
                               ▼
                    ┌──────────────────────┐
                    │  ai-agent/graph/      │  LangGraph StateGraph,
                    │  graph.py + routes.py │  MemorySaver checkpointer
                    └──────────┬───────────┘
                               │
                     ┌─────────┴──────────┐
                     ▼                    ▼
              ai-agent/nodes/*      ai-agent/prompts/*.md
              (9 nodes; 4 call        (system prompts for the
               an LLM, 5 don't —       4 LLM nodes)
               Section 22 Principle 1)
                     │
                     ▼
            ai-agent/mcp_integrations/
              client.py  -- generic stdio MCP session helper
              tools.py   -- domain calls nodes actually import
              github_client.py -- separate: remote streamable-HTTP,
                                  not spawned locally
                     │
        ┌────────────┼─────────────────────┐
        ▼            ▼                     ▼
  observability-   remediation-       GitHub's own remote
  server (stdio)   server (stdio)     MCP server (HTTP)
        │                │                  │
        ▼                ▼                  ▼
   Prometheus :9090   restart_service()  list_commits / get_commit
   + demo-service       kills/relaunches   (deployment-hypothesis
   /actuator/*          demo-service        evidence)
        │
        ▼
  demo-service (Spring Boot, :8080)
    OrderController      -- POST/GET /orders
    FaultInjectionFilter -- FAULT_LATENCY_MS / FAULT_ERROR_RATE,
                             env-driven, real Thread.sleep()/5xx
    Actuator + Micrometer -- /actuator/health, /actuator/prometheus
```

## Layer by layer

**demo-service** (`demo-service/`) — real Spring Boot 4 app, in-memory
order store, no fake data anywhere. `FaultInjectionFilter` is the one
deliberately-fake piece, and even that produces *real* symptoms (a real
sleep, a real 5xx, a real log line) rather than fabricated metrics —
Section 12's explicit requirement.

**Prometheus** (`prometheus/`) — pull-based scrape of
`/actuator/prometheus` every 5s. This is what makes the observability
MCP's windowed queries (`rate(...)[5m]`, `histogram_quantile`)
meaningful instead of instantaneous-only.

**mcp-servers/** — two local stdio MCP servers (`observability-server`,
`remediation-server`), each a thin wrapper: reads go through Prometheus
+ Actuator + the log file; the one write (`restart_service`) shells out
to kill/relaunch the Maven process. No approval logic lives here on
purpose (see `docs/learning-notes.md` Phase 3 Step 9) — that's the
agent layer's job.

**ai-agent/mcp_integrations/** — the client side of that boundary.
`client.py` has both a `mcp_session()` (spawn a local server over stdio)
and a `github_mcp_session()` (streamable-HTTP + bearer token, for a
server GitHub operates rather than one this repo hosts) — same
`ClientSession` API either way, only the transport differs. `tools.py`
is what graph nodes actually import: one session per logical need, not
per tool call, including `get_recent_deployment_evidence()` (real
`list_commits`/`get_commit` calls, feeding
`investigate_hypothesis()`'s deployment branch).

**ai-agent/graph/ + ai-agent/nodes/** — the LangGraph workflow itself:
9 nodes matching `PLAN.md` Section 11 one-to-one, wired by
`graph/graph.py`, routed by `graph/routes.py`. Two structural things
worth calling out because they're the actual reason this needed
LangGraph rather than a linear script (Section 22 Principle 4):

- **The investigation loop** (`route_after_evaluate`): if
  `evaluate_evidence`'s confidence is below 0.7, the graph loops back
  through `generate_hypotheses` (now fed the accumulated
  `investigation_results`, not just the initial snapshot) and
  `investigate` again, capped at 2 passes.
- **The approval interrupt** (`nodes/human_approval.py`): LangGraph's
  `interrupt()` unwinds execution back to `main.py` with a checkpoint
  saved; `main.py` is the only place that calls `input()`, and resumes
  the same run with `Command(resume=...)`.

**ai-agent/main.py** — the one CLI entry point tying it together:
invoke, loop on `"__interrupt__"` in the result, print the
recommendation, prompt, resume, print the final summary.

## What's spec shape but not yet real

- **Docker** (`PLAN.md` Section 18): everything above runs natively.
  Explicitly optional per the spec ("containerize only if time
  permits... do not spend hours debugging container networking").
- **`rollback_version()`**: not implemented — there's no versioned
  artifact to roll back to yet (no Docker image history). Only
  `restart_service()` exists, which is why Scenario 2's remediation
  step (see `docs/demo-script.md`) doesn't actually fix an
  env-var-driven fault — a good live illustration of *why* the spec
  distinguishes the two actions.
