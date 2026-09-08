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
`ai-agent/mcp/github_client.py`

**Not yet verified live** — no `GITHUB_TOKEN` configured. This is the
one Phase 3 piece that's genuinely different from Steps 7/9: it connects
to a server GitHub operates (`https://api.githubcopilot.com/mcp/`) over
streamable-HTTP with a bearer token, instead of a local stdio subprocess.
The code deliberately avoids hardcoding exact tool names (GitHub's own
naming for "list commits" isn't pinned in this codebase) and instead
searches the live `list_tools()` result — since Step 8's actual learning
objective, per the spec, is "understand how an agent discovers and calls
tools exposed by an *external* MCP server," which the local stdio
examples (Steps 3, 7, 9) can't teach: there, you wrote both sides, so
there was never really any discovery required. Once a token is set, run
it and fill in what the real tool names turned out to be — that answer
belongs here, not guessed in advance.

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

Not yet built — see `PLAN.md` Sections 19/20 for the step sequence and
the plan file for current status. Add notes here once there's a working
end-to-end run, answering the spec's per-node "learning" callouts
(Section 11) and the Section 23 evaluation questions.
