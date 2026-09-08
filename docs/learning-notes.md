# Learning Notes

Answers to the spec's "learning questions," recorded per phase/step as
they're built. This is a running document — update it as later phases
land, don't just leave Phase 1's answers standing alone.

---

## Phase 1, Step 1 — LangChain basics
`ai-agent/step1_langchain_basics.py`

**What does LangChain abstract away?**
Three things, concretely, in that one script:
- **Provider-agnostic model interface.** `ChatAnthropic` implements the
  same `BaseChatModel` interface every other integration does. Swap it
  for `ChatOpenAI` and the prompt, the chain, and `with_structured_output`
  call don't change — only the constructor line does.
- **Prompt templating.** `ChatPromptTemplate` separates the fixed prompt
  *shape* (system role + a `{signal}` slot) from the data filled into it
  at call time, instead of you hand-building a message list/f-string
  every call site.
- **Structured output enforcement.** `with_structured_output(Model)`
  wraps the raw API's tool-calling/JSON-mode machinery so you get back a
  validated Pydantic instance, not a string you then have to
  `json.loads()` and hope didn't hallucinate a field.

**What could you do directly with the model SDK instead?**
Call `anthropic.Anthropic().messages.create(...)` directly, build the
message list by hand, ask for JSON in the system prompt, and
`json.loads()` + manually validate the response. That's a legitimate
choice for a single fixed call site with one provider. The cost shows up
as the project grows: every prompt becomes ad-hoc message-building code,
every structured call gets its own hand-rolled parsing/retry logic, and
switching providers means rewriting call sites instead of one line.

**Why use structured output instead of "reply in JSON" + manual parsing?**
Two failure modes it removes: (1) the model wrapping JSON in prose or
markdown fences, breaking a naive `json.loads()`; (2) fields with the
wrong type or a missing required field passing through silently. Pydantic
validation makes both failures loud (an exception) at the call site
instead of a wrong type sneaking downstream into a graph node that
assumes `severity` is always one of four strings.

---

## Phase 1, Step 2 — LangGraph basics
`ai-agent/step2_langgraph_basics.py`

**What is a node?**
A plain function `(state) -> partial_state_update`. `analyze`,
`investigate`, and `mark_healthy` are all just functions — nothing about
them requires an LLM. That's deliberate: this step's routing decision
(`latency_ms > 500`) is a threshold check, not a model call, to show that
LangGraph's value (state + control flow) is independent of whether any
given node happens to call an LLM.

**What is an edge?**
A fixed transition: `graph.add_edge("investigate", END)` always goes
`investigate -> END`, no decision involved.

**What is conditional routing?**
`add_conditional_edges("analyze", route_after_analyze, {...})` — a
function that inspects state and returns a key, and a dict mapping that
key to the next node. This is how the graph forms an actual decision
tree instead of a straight-line pipeline (a LangChain LCEL chain like
Step 1's can't branch like this).

**What is graph state?**
The shared `TriageState` TypedDict every node reads and returns updates
to. Each node gets the *whole* current state as input but typically
returns only the keys it changed — LangGraph merges the update in. This
is what lets `investigate` see the `notes` `analyze` already wrote,
without either function knowing the other exists.

---

## Phase 1, Step 3 — MCP basics
`ai-agent/step3_mcp_basics/{server.py,client.py}`

**How are tools advertised?**
The server declares them (`@server.tool()` on `get_current_time`); the
client never hardcodes what tools exist — it calls `session.list_tools()`
and gets back names, descriptions, and JSON schemas at runtime. This is
the actual mechanism behind "an LLM can call tools it's never seen
before": the tool list from `list_tools()` is what gets handed to the
model as its available-tools schema.

**How does the client discover tools?**
`ClientSession.initialize()` performs the MCP handshake (protocol
version negotiation, capability exchange) — only after that does
`list_tools()` return anything.

**How are arguments passed?**
`call_tool("get_current_time", arguments={})` — a plain dict, validated
against the tool's declared schema before your function body ever runs.

**How are results returned?**
As a list of typed content blocks (`result.content`) — text here, but the
protocol supports images and embedded resources too, which is why
results aren't just "a string."

**What transport is being used?**
stdio: the client (`stdio_client`) owns the server's process lifecycle —
it launches `server.py` as a subprocess and speaks newline-delimited
JSON-RPC over its stdin/stdout. This is the right transport for a tool
that lives on the same machine as the client. A server another team
operates (like GitHub's MCP server, Phase 3 Step 8) instead runs
independently and is reached over HTTP/SSE — same client-side API
(`ClientSession`), different transport underneath.

---

## Phase 1, Step 4 — LangSmith
`ai-agent/step4_langsmith_tracing.py`

**Why is application logging insufficient for AI agent systems?**
A log line records *that* a function ran and maybe its return value. It
doesn't record the exact rendered prompt (with all the system/few-shot
text a template produced), the model's raw response before your parser
touched it, which of several possible graph branches got taken and why,
or what it cost in tokens/latency. When an agent's output is wrong, the
question is almost always "what did the model actually see, and what did
it actually say back" — and that's precisely the Trace/Run/Span
input-output pair LangSmith captures automatically, with no manual log
statements added to the chain code.

*(To be filled in once `LANGCHAIN_API_KEY` is set and a real trace has
been inspected in the UI: note here what the graph execution path view
actually looks like for Step 1/2, and whether anything about the traced
inputs/outputs was surprising.)*

---

## Phase 2, Step 5 — Spring Boot Order Service
`demo-service/`

**Why build this at all, instead of mocking metrics/logs directly?**
The spec is explicit (Section 12): "Do not randomly return fake JSON."
The whole point of Phase 3's observability MCP server and Phase 4's
evidence-gathering node is to prove an agent can pull *real* signal out
of a *real* running system through a *real* protocol boundary. A mocked
metrics endpoint would let every later phase "work" without ever proving
that — Prometheus really scraping, MCP really calling out, an LLM really
reasoning over numbers it didn't get handed pre-baked.

**What did Actuator + Micrometer actually give us for free?**
Adding `spring-boot-starter-actuator` + `micrometer-registry-prometheus`
and one line of config
(`management.endpoints.web.exposure.include=health,prometheus,metrics`)
produced fully-labeled per-endpoint metrics
(`http_server_requests_seconds_count{uri="/orders",method="POST",status="201",...}`)
with zero instrumentation code written by hand. This is the same reason
the spec keeps saying "use deterministic/off-the-shelf pieces where the
behavior is deterministic" (Principle 1, Section 22) — request counting
and latency histograms aren't something worth hand-rolling or asking an
LLM to reason about; they're infrastructure.

**Version note (worth recording since it deviates from what most
tutorials show):** Spring Boot's current line as of this build is 4.x
(4.1.1), not the 3.x most existing docs/tutorials reference — Spring
Initializr's metadata rejected 3.x outright (`compatibility range is
>=4.0.0`). Boot 4 renamed the web starter to
`spring-boot-starter-webmvc` (from `spring-boot-starter-web`). Point
release: don't trust a remembered starter name without checking
`start.spring.io`'s current metadata first.

---

## Phase 2, Step 6 — Prometheus scraping
`prometheus/prometheus.yml`

**What makes this "a realistic observability system" per Section 6,
rather than just another HTTP call the agent could make directly?**
Prometheus is a *pull*-based time-series database: it scrapes
`/actuator/prometheus` on its own schedule (`scrape_interval: 5s` here)
and stores history, so a query can ask about a window of time
("error rate over the last 5 minutes"), not just "what is it right now."
That's the actual capability Phase 3's `get_service_metrics()` /
`get_latency_metrics()` tools need and a raw Actuator scrape alone
doesn't give you — Actuator only ever answers "what is the counter's
value at this instant."

**Verified end-to-end** (spec Section 19's exact Step 6 success
criterion — "Spring Boot → Prometheus → Metrics Query → Correct
Result"): the target shows `health: up` in
`GET /api/v1/targets`, and `http_server_requests_seconds_count{application="order-service"}`
returned counts that matched the exact requests just made via curl —
confirming the scrape config's `metrics_path`/`targets` are correct and
Micrometer's Prometheus exposition format is something Prometheus parses
without any translation layer in between.

---

## Phase 3, Step 7 — Observability MCP
`mcp-servers/observability-server/`

**Verified live** against the real running Order Service + Prometheus:
all five tools (`get_application_health`, `get_service_metrics`,
`get_latency_metrics`, `get_error_rate`, `get_recent_errors`) returned
correct, real values (`status: UP`, `p95_latency_ms: 8.9`, error rate
`0.0` — expected, since no fault has been injected yet; that's what
Phase 4's fault injection exists to change).

**Why five tools instead of one big "get everything" tool?** Section 11
Node 2 lists `get_application_health()`, `get_service_metrics()`,
`get_recent_errors()` as separate calls, and Section 11 Node 4 shows
different hypotheses each need *different* evidence (the resource
hypothesis wants `get_service_metrics()`; the DB hypothesis wants
`get_recent_errors()`). A single combined tool would force every graph
node to fetch (and pay LLM context tokens for) evidence it doesn't need.
`get_service_metrics()` still exists as a convenience "first look"
snapshot for the initial-evidence node — but it's a thin composition of
the finer-grained tools, not the only way to get at the data.

**Why did `get_latency_metrics()` need a Spring Boot config change first
(`percentiles-histogram.http.server.requests=true`)?** Without it,
Micrometer only exports the running sum and count for
`http_server_requests_seconds` — enough for an *average*, not a
percentile. `histogram_quantile()` needs `_bucket` series (a
distribution), which only exist once that property turns histogram
export on. This is a concrete instance of the general lesson: an MCP
tool is only as good as the data actually available underneath it — the
protocol doesn't conjure data the source system isn't emitting.

---

## Phase 3, Step 8 — GitHub MCP
`ai-agent/mcp_integrations/github_client.py`

**Verified live.** This is the one Phase 3 piece that's genuinely
different from Steps 7/9: it connects to a server GitHub operates
(`https://api.githubcopilot.com/mcp/`) over streamable-HTTP with a
bearer token, instead of a local stdio subprocess. The code deliberately
avoids hardcoding exact tool names (GitHub's own naming for "list
commits" isn't pinned in this codebase) and instead searches the live
`list_tools()` result — since Step 8's actual learning objective, per
the spec, is "understand how an agent discovers and calls tools exposed
by an *external* MCP server," which the local stdio examples (Steps 3,
7, 9) can't teach: there, you wrote both sides, so there was never
really any discovery required.

**What came back:** 44 tools total (far more than the read-only handful
this POC needs — GitHub's server also covers PRs, issues, releases,
branches, secret scanning, etc.). The two relevant to Section 12
Scenario 4 turned out to be `list_commits` (returns a JSON *list* of
commit summaries, not a dict — `mcp_integrations/client.py`'s
`call_tool()` return type was widened from `dict` to `Any` because of
this) and `get_commit` (returns `{sha, html_url, commit, author,
committer, stats, files}`, where `files` is a list of `{filename,
status, additions, changes}` per changed file — no `patch`/diff content,
just the file list and line-count deltas, which is enough to correlate
"this commit touched the service" without spending prompt tokens on full
diffs). Both are now wired into
`mcp_integrations/tools.py:get_recent_deployment_evidence()`, called
from `investigate_hypothesis()`'s deployment-hypothesis branch — see the
Phase 4 GitHub-correlation section below for the live end-to-end result.

---

## Phase 3, Step 9 — Remediation MCP
`mcp-servers/remediation-server/`

**Verified live**: `restart_service()` killed the real Order Service
process (pid captured beforehand), relaunched it via `mvn
spring-boot:run`, and polled `/actuator/health` until it reported `UP`
again — full round trip in 4.2s.

**Why `restart_service()` and not `rollback_version()` as the spec's
alternative suggests?** `rollback_version()` presumes there's a previous
versioned artifact to roll back *to* — normally a prior container image.
This POC has no Docker/image versioning yet (deferred per Section 18),
so implementing `rollback_version()` now would mean faking the one part
of the system meant to be real. `restart_service()` needed nothing
faked. Phase 4's fault-injection work (Section 12, Scenario 4 —
deployment regression) is exactly where a real "previous version" will
start to exist, at which point `rollback_version()` becomes buildable
the same honest way.

**Where is the human-approval gate?** Deliberately not in this server.
Section 22 Principle 3 draws the READ-vs-WRITE line at the *agent*
layer, not the tool layer — the server's job is only to safely implement
the mechanism; deciding *whether* to call it belongs to the LangGraph
interrupt node (Phase 4, Section 11 Node 7). Testing it here by calling
`restart_service()` directly, with no approval step at all, was
deliberate — it isolates "does the action itself work" from "is the
approval gate wired correctly," which get debugged separately.

---

## Phase 4

`ai-agent/graph/`, `ai-agent/nodes/`, `ai-agent/mcp_integrations/`,
`ai-agent/prompts/`, `ai-agent/main.py`

**Why `ai-agent/mcp/` had to be renamed to `ai-agent/mcp_integrations/`
before this phase could import anything:** a directory literally named
`mcp` sitting next to `main.py` (which becomes `sys.path[0]`) shadows
the *installed* `mcp` SDK package — `from mcp import ClientSession`
inside our own `mcp_integrations/client.py` started resolving to
itself instead of the real SDK. Confirmed empirically (`cannot import
name 'tools' from 'mcp'`) before renaming. Lesson: a local package name
that collides with a third-party import is a real, not theoretical,
footgun the moment its directory is importable (i.e. sits next to the
entry-point script or is otherwise on `sys.path`).

**Verified live** (no `ANTHROPIC_API_KEY` configured in this checkout,
so this covers everything *except* the four LLM-calling nodes):
- `nodes/gather_evidence.py`, `nodes/investigate.py`,
  `nodes/execute_remediation.py`, `nodes/validate.py` — each ran for
  real against the running Order Service + Prometheus. `investigate()`'s
  keyword dispatch (`mcp_integrations/tools.py`) correctly pulled
  `recent_errors` + `latency_metrics` for a "database" hypothesis and
  fell through to `latency_metrics` alone for a "resource exhaustion"
  one.
- The `interrupt()` / `Command(resume=...)` / `MemorySaver` mechanics in
  `nodes/human_approval.py` + `main.py`, isolated in a throwaway
  two-node graph first (langgraph 1.2.11 confirmed): `.invoke()` returns
  `{"__interrupt__": (Interrupt(value=...),)}` rather than raising, and
  a second `.invoke(Command(resume=...), config)` on the *same*
  `thread_id` resumes from exactly that node.
- The full graph, end-to-end, with the four LLM nodes monkeypatched to
  stub functions (so routing/looping could be tested without a real API
  key): a first low-confidence `evaluate_evidence` correctly routed back
  through `generate_hypotheses` → `investigate` (Step 13's loop; also
  confirms `generate_hypotheses`'s merge-not-replace logic keeps the
  original hypothesis around across the loop) rather than straight to
  remediation, a second high-confidence pass proceeded to
  `plan_remediation` → interrupted for approval, and resuming with
  `"yes"` drove a **real** `restart_service()` call against the actual
  local Order Service (it came back `UP` within the timeout, same as
  Phase 3's isolated test) followed by a correct before/after
  `final_summary`.

**Why does `generate_hypotheses` merge new hypotheses into the existing
list instead of replacing it on a loop-back pass, and why does it get
fed `investigation_results` on that second call?** Section 8's "No"
branch out of "Enough Evidence?" only makes sense as a real loop (Step
13 explicitly names this "one of the main reasons to use LangGraph") if
the second pass has something the first didn't — otherwise re-running
`generate_hypotheses` against the *same* initial evidence snapshot would
just reproduce the same hypotheses and the loop would spin without
converging. Feeding it the accumulated `investigation_results` lets it
propose hypotheses that are actually informed by what's been ruled in or
out; merging (keyed by `description`) rather than overwriting means
`investigate()`'s "skip already-investigated" dedup still sees the full
history instead of losing track of what round one covered.

**Why is `nodes/execute_remediation.py` and `nodes/validate.py`'s only
gate the interrupt in `human_approval.py`, not something in `routes.py`
before it?** `route_after_approval` only reads `state["human_approved"]`
— it can't itself decide *whether* to ask, because "whether an action
needs approval" is a property of the plan (`remediation_plan`), not of
the routing step. `human_approval.py` folding that check in (skip the
interrupt entirely when the plan is `NONE` or already says no approval
needed) keeps "was permission required" and "was permission granted" as
one node's responsibility instead of splitting it across two.

**Not yet verified live:** the four LLM nodes
(`understand_incident`, `generate_hypotheses`, `evaluate_evidence`,
`plan_remediation`) and their prompts — needs `ANTHROPIC_API_KEY` (see
README "Running Phase 4"). Once run, this section should get an update
with what a real hypothesis/root-cause/remediation output actually
looked like for at least the healthy and injected-fault scenarios
(Section 21), plus the Section 23 evaluation-criteria answers.

---

## Phase 4, Fault Injection (Section 12)

`demo-service/src/main/java/com/example/orderservice/FaultInjectionFilter.java`,
`scripts/inject_latency.sh`, `scripts/inject_failure.sh`,
`scripts/clear_faults.sh`, `scripts/generate_load.py`

**Verified live, full chain, both fault types:** restart with
`FAULT_LATENCY_MS=2000` → `generate_load.py` → observability MCP's
`get_service_metrics()` reported `status: DEGRADED, p95_latency_ms:
2120.0` (client-observed p95 was 2016ms — the small gap is real
network/JVM overhead on top of the injected sleep, not error). Same for
`FAULT_ERROR_RATE=0.3`: `get_recent_errors()` returned real
`FaultInjectionFilter`-logged `ERROR` lines, and `get_service_metrics()`
again reported `DEGRADED`.

**Why a servlet `Filter` instead of adding the fault check inside
`OrderController`?** It runs identically for every endpoint without
touching business-logic code, and — more importantly — it still sits
*inside* the request/response cycle that Micrometer's own metrics filter
wraps, so `sendError()` here produces a real 5xx that Micrometer records
correctly by status code. The alternative (throwing an exception from
the controller) would need an `@ExceptionHandler` to get the status code
right and adds noise to the one file that's supposed to just be the
"real business logic."

**A real surprise worth recording:** right after switching from
`FAULT_LATENCY_MS=2000` to `FAULT_ERROR_RATE=0.3` (a full process
restart in between), `get_service_metrics()` still showed
`p95_latency_ms: 2096.6` even though the *new* process had no latency
fault active. This isn't a bug — Prometheus's `rate(...)[5m]` window is
time-based, not process-based: the TSDB kept the previous process's
samples and blended them with the new ones because both scrapes hit the
same `job`/`instance` label within the same 5-minute window. Restarting
the *service* does not reset the *metrics history* — a real thing to
account for when reading "before vs. after remediation" numbers close
together in time, and a good live talking point for why
`nodes/validate.py`'s before/after diff should ideally wait out a full
window, or query a narrower one, right after a restart.

**Why is `generate_load.py` a separate script instead of folding traffic
generation into the inject scripts?** A fault alone doesn't move any of
Prometheus's `rate()`-based queries — `get_latency_metrics()` and
`get_error_rate()` are windowed rates over *requests that actually
happened*, so "inject the fault" and "produce the traffic that reveals
it" are genuinely two different concerns; the demo script
(`docs/demo-script.md`) runs them as separate terminals on purpose, the
same way a real degraded service needs real user traffic hitting it
before a dashboard shows anything.

**Not done:** Scenario 4's git-commit correlation half — this needs
`GITHUB_TOKEN` (still unset in this checkout) and wiring an actual
GitHub MCP call into `nodes/investigate.py`'s deployment-hypothesis
branch, which currently only leaves a placeholder note. See
`docs/demo-script.md` Scenario 3 for the concrete remaining steps.

---

## Phase 4, LLM verification (`ai-agent/llm.py`, `ANTHROPIC_API_KEY` → local Ollama)

**Two Anthropic dead ends before a working key:** the first key given was
org-level, not scoped to a workspace (`anthropic-workspace-id` header
required) — Anthropic's API always resolves a request against exactly
one workspace and won't guess which. The second, workspace-scoped key
hit a $0 credit balance instead. Neither is a code problem; both are
Anthropic Console account state.

**Switched to a local model instead** (Ollama + `qwen2.5`, already
installed and pulled on this machine) rather than paying to unblock
Anthropic, since the goal here is learning the orchestration, not the
specific model vendor — which is itself the point of `ai-agent/llm.py`:
one `get_llm()` function reading `LLM_PROVIDER` from `.env`, so all four
LLM nodes (`understand_incident`, `generate_hypotheses`,
`evaluate_evidence`, `plan_remediation`) get their model from one place
instead of each constructing `ChatAnthropic(...)` directly. Concretely
answers Section 23's "did LangChain simplify model interaction?" — yes,
enough that swapping providers touched one file instead of four.

**A real structured-output gap this surfaced:** `qwen2.5` does not
reliably honor an enum stated only in a Pydantic field's `description`
string — asked for `priority: one of low/medium/high/critical`, it
returned `'High Urgency - Immediate Attention Required'`. Claude had
never shown this failure mode in testing, which is exactly why it went
unnoticed until swapping models. The fix was making the fields
themselves `Literal["low", "medium", "high", "critical"]` etc.
(`nodes/understand_incident.py`, `nodes/remediation.py`) rather than
free `str` fields — that constraint goes into the actual JSON schema
`with_structured_output` sends the model, not just the prompt text, and
qwen2.5 honored it exactly on retest. Worth calling out as a general
lesson, not an Ollama-specific one: anywhere a structured-output field's
value is later compared by exact equality in code (`nodes/human_approval.py`'s
`plan.get("action") == "NONE"`, `routes.py`), the schema should enforce
that constraint, not just the prompt — weaker models expose this gap
first, but a strict schema is strictly better on stronger models too, at
no real cost.

**Verified live end-to-end, all three Section 21 scenarios, real LLM
calls throughout, on `qwen2.5` via Ollama:**

- **Scenario 1 (healthy):** `evaluate_evidence` reported 100% confidence
  in "no significant incident," `plan_remediation` returned `NONE`, no
  approval prompt appeared (correctly skipped by
  `nodes/human_approval.py`), final summary reported `UP`.
- **Scenario 2 (latency, 2000ms injected + real traffic):**
  `gather_evidence` saw `DEGRADED`/`p95_latency_ms: 2118`; the model
  diagnosed "increased load... recent surge in traffic" at 70%
  confidence (plausible from the evidence alone — it has no visibility
  into the injected fault, which is the point) and proposed
  `RESTART_SERVICE`. Approved via the real interrupt/resume path; the
  real `restart_service()` ran; `validate` correctly reported **STILL
  DEGRADED** afterward (`p95_latency_ms: 2118.9`, essentially
  unchanged) — a genuine, honest demonstration of why an env-var-driven
  fault needs `rollback_version()`-style remediation, not
  `restart_service()`, and validation correctly caught that the action
  didn't work instead of reporting false success.
- **Scenario 3 (30% injected errors + real traffic):** the model
  actually read the literal `FaultInjectionFilter`-logged line
  ("Injected fault: simulated failure...") out of `get_recent_errors()`
  and concluded "Simulated fault injection is causing degraded
  performance" at 80% confidence, then correctly proposed `NONE` (a
  process restart doesn't fix a config-driven fault) — no approval
  interrupt fired, matching `nodes/human_approval.py`'s designed
  behavior for a no-action plan. Separately confirmed the reject path
  itself works (a manual `"n"` response during Scenario 2 testing
  correctly routed to `skip_execution` → validate's no-action branch)
  before this run took the no-interrupt path on its own.

**A restart-script bug this testing found and fixed:**
`scripts/_restart-order-service.sh` originally found only the java child
process via `lsof` on :8080 and killed just that — but `mvn
spring-boot:run` is two processes (the mvn wrapper + the java child it
forks), and the wrapper stays alive briefly after the child dies,
writing its own "process terminated with exit code: 143" line to
`/tmp/order-service.log` right as the *next* invocation's `>` redirect
truncates that same file — a genuine race that corrupted the log file
(binary garbage) during earlier fault-injection testing and would have
fed that garbage straight into `get_recent_errors()` → the hypothesis
LLM prompt. Fixed by matching both processes with `pkill -f
"spring-boot:run"` and waiting on `pgrep`, not just the port, before
truncating.

---

## Phase 4, LangSmith tracing (Section 16, Section 25 step 18)

**Verified live**: `LANGCHAIN_TRACING_V2=true` + a real `LANGCHAIN_API_KEY`
in `ai-agent/.env`, confirmed by querying the LangSmith API directly
(`client.list_runs(project_name=...)`) rather than just trusting that the
script didn't error -- the run tree for one `ai-agent/main.py` invocation
showed exactly the nesting Section 16 describes: one `chain` run per
LangGraph node (`understand_incident`, `gather_evidence`,
`generate_hypotheses`, `investigate`, `evaluate_evidence`,
`plan_remediation`, `human_approval`, `validate`), each conditional edge
(`route_after_evaluate`, `route_after_approval`) as its own run, and each
LLM node's internals as a nested `RunnableSequence` →
`ChatPromptTemplate` → `ChatOllama` → `PydanticOutputParser` chain --
i.e. the exact rendered prompt and raw model output are inspectable per
node, not just the parsed result the node returns.

**Also had to retrofit `step1_langchain_basics.py`'s Step 4 companion
script** (`step4_langsmith_tracing.py`) to use `llm.py`'s `get_llm()`
instead of a hardcoded `ChatAnthropic(...)` -- it predates `llm.py`
(built in this same phase) and would otherwise have needed
`ANTHROPIC_API_KEY` specifically to demonstrate tracing at all, even
though tracing itself has nothing to do with which model is behind it.

**A real gap this surfaced, worth knowing before relying on tracing for
debugging:** MCP tool calls (`mcp_integrations/tools.py`, used by
`gather_evidence`/`investigate`/`execute_remediation`/`validate`) do
**not** appear as their own runs in the trace -- they're plain `asyncio`
calls to a subprocess over stdio, not LangChain `Runnable`s, so
LangSmith's automatic instrumentation has nothing to hook. The trace
shows "this node ran and returned X," not "this node called
`get_service_metrics()` which called Prometheus" -- exactly the boundary
LangChain's callback system covers (LLM calls, prompts, parsers, chains)
versus what it doesn't (arbitrary I/O a node happens to do). A
production version wanting MCP calls in the trace too would need to wrap
them as `@tool`-decorated LangChain tools or manually create child runs
with the LangSmith SDK -- neither done here, since the nodes call
`mcp_integrations.tools` directly rather than exposing them as
LangChain-visible tool objects (a deliberate Section 22 Principle 1
choice: these calls are deterministic dispatch, not something an LLM
chooses to invoke, so they were never modeled as agent-facing "tools" in
the LangChain sense to begin with).

---

## Phase 4, deployment-regression correlation (Section 12 Scenario 4)

`mcp_integrations/tools.py:get_recent_deployment_evidence()`, wired into
`investigate_hypothesis()`'s deployment branch (replacing the earlier
placeholder note).

**Verified live, full path:** ran `ai-agent/main.py` with an incident
description phrased to suggest a deployment cause
("...possibly a code regression"). `generate_hypotheses` proposed
"Deployment introduced a regression..." at 70% confidence;
`investigate()` dispatched to `get_recent_deployment_evidence()`, which
made two real calls to GitHub's remote MCP server
(`list_commits` → `get_commit`) and returned the actual latest commit's
message and 30 changed files; that evidence landed in
`investigation_results` and was available to `evaluate_evidence`'s
prompt — confirmed directly by calling the nodes in sequence and
inspecting state between them, not just trusting the final output.

**A limitation worth flagging before using this for a real demo:** GitHub
MCP only sees what's actually on the *remote* — `list_commits` returned
exactly one commit (`6cd80a2`, "Phases 1-3") because this checkout's
later commits (Phase 4's graph, fault injection, the Ollama switch) were
all still local/unpushed at the time of this test. A live Scenario 4 run
needs `git push` first, or the "recent deployment" the agent finds won't
match what's actually running. (Neat framing this makes possible once
pushed: the `FaultInjectionFilter.java` commit itself becomes a
plausible "regression commit" for the agent to correctly point at.)

**Also worth flagging — a genuine model-honesty gap, not a wiring bug:**
a separate run with the *same* suggestively-worded incident description
but no fault actually injected produced an 80%-confidence root cause
("resource contention or misconfiguration") that the evidence didn't
clearly support — `metrics.status` was `HEALTHY` the whole time.
`prompts/hypothesis_generation.md` explicitly instructs proposing "no
significant incident" when metrics are healthy, but a suggestive
incident description text apparently outweighed the actual evidence for
this model. Worth checking whether Anthropic's models are more resistant
to this once billing is sorted — but either way it's a real answer to
Section 23's "how honest is the agent about uncertainty?" evaluation
question, and a good demo talking point about why the evidence, not the
prompt, should be trusted.
