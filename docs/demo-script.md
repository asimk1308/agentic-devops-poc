# Demo Script

Walkthroughs for the three scenarios in `PLAN.md` Section 21, using what's
actually built (see `docs/architecture.md` for the real vs. planned
picture, `docs/learning-notes.md` for what's been verified live so far).

All three assume infra is up:

```bash
scripts/start-infra.sh
```

And, for Scenarios 2/3's AI-agent half, an LLM configured in
`ai-agent/.env` (see README "One-time setup" — `LLM_PROVIDER=ollama` is
what's actually verified in this checkout). Scenario 3's git-correlation
half additionally needs `GITHUB_TOKEN`/`GITHUB_REPO`.

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

**Status: fully wired and verified live** —
`get_recent_deployment_evidence()` (`mcp_integrations/tools.py`) calls
GitHub's MCP server's real `list_commits`/`get_commit` tools and feeds
the result into `investigate_hypothesis()`'s deployment branch; confirmed
end-to-end by inspecting `investigation_results` directly (see
`docs/learning-notes.md`). **Important caveat before running this for a
demo:** GitHub MCP only sees what's on the *remote* — `git push` first,
or the "recent commit" the agent finds won't match your actual local
changes.

```bash
# Push first (see caveat above)
git push

scripts/inject_failure.sh 0.3
python3 scripts/generate_load.py --duration 20 --rate 8
ai-agent/.venv/bin/python ai-agent/main.py \
  "Investigate Order Service - errors started right after the last deployment."
scripts/clear_faults.sh   # reset after
```

Expected: `generate_hypotheses` proposes a deployment-regression
hypothesis; `investigate()` dispatches to
`get_recent_deployment_evidence()` and pulls the real latest commit
(message + changed files) from GitHub; `evaluate_evidence` should cite
that commit alongside the error-rate evidence rather than treating them
separately.

To make this maximally concrete for a live demo, push a commit that
*actually* looks like the regression being diagnosed — e.g. temporarily
hardcoding a bad default into `FaultInjectionFilter.java` instead of
reading it from the environment — so the commit GitHub MCP surfaces is
the same one causing the symptoms, and `git revert` becomes the
demonstrated remediation instead of (or alongside) `restart_service()`.

---

## After any scenario

`scripts/clear_faults.sh` resets the Order Service to a clean state.
`scripts/stop-infra.sh` stops both processes entirely.
