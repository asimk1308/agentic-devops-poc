# Demo Script

Walkthroughs for the three scenarios in `PLAN.md` Section 21, using what's
actually built (see `docs/architecture.md` for the real vs. planned
picture, `docs/learning-notes.md` for what's been verified live so far).

All three assume infra is up:

```bash
scripts/start-infra.sh
```

And, for Scenarios 2/3's AI-agent half, `ANTHROPIC_API_KEY` set in
`ai-agent/.env` (see README "One-time setup").

---

## Scenario 1 — Healthy

No fault injected. Confirms the agent doesn't invent a problem when
there isn't one (Section 12's warning against fabricated incidents,
`prompts/hypothesis_generation.md`'s explicit "it is entirely correct to
say so" instruction).

```bash
ai-agent/.venv/bin/python ai-agent/main.py "Investigate Order Service."
```

Expected: `evaluate_evidence` reports high confidence in something like
"no significant incident: metrics are within normal range,"
`plan_remediation` proposes `NONE`, no approval prompt appears (Node 7
skips the interrupt when the plan needs no approval — see
`nodes/human_approval.py`), and `validate`'s final summary reflects the
no-action branch.

---

## Scenario 2 — Performance Issue (latency)

```bash
# Terminal 1: inject the fault (restarts order-service)
scripts/inject_latency.sh 2000

# Terminal 2: generate real traffic so Prometheus's rate()-based queries
# have something to measure (see docs/learning-notes.md on why fault
# injection alone doesn't move them)
python3 scripts/generate_load.py --duration 20 --rate 5

# Terminal 1, once load has run a few seconds: run the agent
ai-agent/.venv/bin/python ai-agent/main.py "Investigate performance degradation in Order Service."
```

Expected: `gather_evidence` sees `metrics.status: DEGRADED` and an
elevated `p95_latency_ms`; `generate_hypotheses` should propose something
resource/latency-shaped; `evaluate_evidence` should land on a
performance-regression root cause; `plan_remediation` proposes
`RESTART_SERVICE` (restarting won't actually fix an env-var-driven
fault, which is worth noticing live — this is where a real
`rollback_version()` would differ from `restart_service()`, see
`docs/learning-notes.md` Phase 3 Step 9).

Reset before the next scenario:

```bash
scripts/clear_faults.sh
```

---

## Scenario 3 — Deployment Regression (primary demo)

This is the scenario `PLAN.md` Section 21 calls out as primary, because
it's the one that makes GitHub MCP genuinely load-bearing rather than
decorative: the root cause isn't just "latency is high," it's "latency
is high *and* it started right after this specific commit."

**Status: partially runnable today.** The error-injection half
(`scripts/inject_failure.sh`) is built and verified live (see
`docs/learning-notes.md`). The git-correlation half needs
`GITHUB_TOKEN`/`GITHUB_REPO` configured (`ai-agent/.env`) and
`ai-agent/mcp_integrations/github_client.py` run once to confirm which
tool names GitHub's MCP server actually exposes — neither has happened
in this checkout yet.

Runnable today (error-regression half):

```bash
scripts/inject_failure.sh 0.3
python3 scripts/generate_load.py --duration 20 --rate 8
ai-agent/.venv/bin/python ai-agent/main.py "Investigate errors in Order Service."
scripts/clear_faults.sh   # reset after
```

To complete the git-correlation half once `GITHUB_TOKEN` is set:

1. Make a real, small regression commit — e.g. temporarily hardcode a
   bad default in `FaultInjectionFilter.java` instead of reading
   `FAULT_ERROR_RATE` from the environment — and commit it.
2. Restart the service (the commit is now "deployed").
3. Run `ai-agent/mcp_integrations/github_client.py` to confirm the real
   tool names, then wire a `get_recent_commits()`/`get_changed_files()`
   call into `nodes/investigate.py`'s deployment-hypothesis branch (it
   currently only leaves a `git_note` placeholder there — see the
   comment in `mcp_integrations/tools.py`'s `investigate_hypothesis`).
4. Run the agent and confirm `evaluate_evidence`'s evidence list cites
   the actual commit.
5. `git revert` the regression commit as the demonstrated remediation,
   instead of (or alongside) `restart_service()`.

---

## After any scenario

`scripts/clear_faults.sh` resets the Order Service to a clean state.
`scripts/stop-infra.sh` stops both processes entirely.
