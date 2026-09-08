# Agentic DevOps Incident Response POC

## Master Technical Planning, Learning, and Development Guide

---

# 1. Project Overview

## Project Name

**Agentic DevOps Incident Response Platform**

## Project Goal

Build a realistic Proof of Concept demonstrating how modern Agentic AI technologies can be used to investigate and respond to application incidents.

The POC must demonstrate meaningful usage of:

* LangChain
* LangGraph
* LangSmith
* Model Context Protocol (MCP)
* Spring Boot
* Prometheus
* Docker

The system should not be a simple chatbot.

Instead, it should demonstrate a stateful, tool-driven, agentic workflow capable of:

1. Receiving an incident
2. Understanding the incident
3. Gathering evidence from multiple systems
4. Generating possible root-cause hypotheses
5. Investigating those hypotheses
6. Evaluating evidence
7. Determining the probable root cause
8. Generating a remediation recommendation
9. Requesting human approval before actions
10. Validating the outcome

---

# 2. Primary Learning Objective

This POC is not only about building a working application.

The developer must understand:

* Why LangChain exists
* Why LangGraph exists separately from LangChain
* Why MCP is needed
* How MCP clients and servers communicate
* How an LLM chooses and invokes tools
* How stateful agent workflows work
* When to use deterministic logic vs LLM reasoning
* How human-in-the-loop workflows work
* Why LangSmith is needed
* How AI agents integrate with existing Java/Spring Boot systems
* How to design safe autonomous systems

The development process should prioritize understanding over blindly generating code.

---

# 3. Business Problem

Modern production systems generate massive amounts of operational data.

When an incident occurs, engineers typically investigate manually.

For example:

```text
Alert Received
      ↓
Check Metrics
      ↓
Check Logs
      ↓
Check Recent Deployments
      ↓
Check Source Code Changes
      ↓
Generate Hypothesis
      ↓
Validate Hypothesis
      ↓
Determine Root Cause
      ↓
Recommend Fix
```

This process is repetitive and requires engineers to manually navigate multiple systems.

The goal of this POC is to explore whether an AI agent can assist with this workflow.

The agent should not blindly execute actions.

Instead:

```text
AI investigates autonomously

↓

AI gathers evidence

↓

AI proposes root cause

↓

AI recommends remediation

↓

Human approves risky action

↓

Action executed

↓

System validates outcome
```

---

# 4. Core Demo Scenario

A Spring Boot application is running locally.

The application is intentionally deployed with a faulty version.

The faulty version causes:

* Increased API latency
* Increased error rate
* Application errors in logs

The user submits an incident request:

> Investigate the performance degradation in Order Service.

The AI agent should autonomously investigate.

Expected workflow:

```text
Incident Received
       │
       ▼
Initial Analysis
       │
       ▼
Gather Runtime Evidence
       │
       ├── Metrics
       ├── Logs
       ├── Health Status
       └── Recent Code Changes
       │
       ▼
Generate Hypotheses
       │
       ├── Database Problem?
       ├── Resource Exhaustion?
       └── Recent Deployment Regression?
       │
       ▼
Investigate Evidence
       │
       ▼
Evaluate Hypotheses
       │
       ▼
Determine Root Cause
       │
       ▼
Generate Remediation Plan
       │
       ▼
Human Approval
       │
       ▼
Execute Approved Action
       │
       ▼
Validate System
```

---

# 5. Technology Architecture

## High-Level Architecture

```text
                              USER
                                │
                                │ Incident Request
                                ▼
                    ┌──────────────────────┐
                    │    AI AGENT API      │
                    │       Python         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      LANGGRAPH       │
                    │ Workflow Orchestrator│
                    └──────────┬───────────┘
                               │
                     ┌─────────┼──────────┐
                     │         │          │
                     ▼         ▼          ▼
                 LangChain    MCP      LangSmith
                     │         │          │
                     │         │          │
                     ▼         ▼          ▼
                    LLM    External      Trace
                           Tools
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
       GitHub MCP       Observability MCP    Action MCP
             │                 │                  │
             ▼                 ▼                  ▼
         GitHub          Prometheus           Docker
                              │                  │
                              ▼                  ▼
                       Spring Boot App     Application Runtime
```

---

# 6. Technology Responsibilities

## Spring Boot

Spring Boot represents the real application being monitored.

Responsibilities:

* REST APIs
* Business functionality
* Health endpoints
* Metrics
* Logs
* Fault simulation

Technologies:

```text
Java
Spring Boot
Spring Boot Actuator
Micrometer
```

The Spring Boot application should expose:

```text
/actuator/health

/actuator/metrics

/actuator/prometheus
```

---

## Prometheus

Prometheus collects real application metrics.

Metrics should include:

```text
HTTP request count

HTTP error count

Request latency

JVM metrics

Application availability
```

Prometheus represents a realistic observability system.

The AI agent should retrieve operational information through tools rather than directly reading arbitrary files.

---

## Python AI Agent

Python contains the Agentic AI orchestration layer.

Responsibilities:

```text
Incident understanding

Workflow orchestration

Hypothesis generation

Tool invocation

Evidence evaluation

Root cause analysis

Remediation recommendation
```

Technologies:

```text
Python
LangChain
LangGraph
LangSmith
MCP Client
```

---

## MCP

MCP provides the standardized interface between the AI agent and external capabilities.

The agent should not directly contain infrastructure-specific integrations.

Instead:

```text
AI Agent
   │
   │ MCP
   ▼
Tool Server
   │
   ▼
External System
```

This abstraction allows the same agent to work with different implementations.

Example:

```text
Agent
   │
   ▼
get_service_metrics()
   │
   ▼
MCP Server
   │
   ├── Prometheus Today
   │
   ├── Datadog Tomorrow
   │
   └── CloudWatch Later
```

---

# 7. MCP Architecture

The POC should use three logical MCP capability domains.

---

## MCP Server 1: Source Control

Purpose:

Access source code and deployment history.

Possible tools:

```text
get_recent_commits()

get_changed_files()

get_commit_details()

get_recent_deployments()
```

For the POC, use an existing GitHub MCP server if possible.

Learning objective:

Understand how an agent discovers and calls tools exposed by an external MCP server.

---

## MCP Server 2: Observability

Purpose:

Provide runtime information.

Tools:

```text
get_application_health()

get_service_metrics()

get_latency_metrics()

get_error_rate()

get_recent_errors()
```

Example response:

```json
{
  "service": "order-service",
  "status": "DEGRADED",
  "error_rate": 12.4,
  "p95_latency_ms": 2450,
  "baseline_latency_ms": 120
}
```

This MCP server can be custom-built.

Initially it should connect to:

```text
Prometheus
Spring Boot Actuator
Application Logs
```

---

## MCP Server 3: Remediation

Purpose:

Expose controlled operational actions.

Tools:

```text
restart_service()

rollback_version()
```

Important safety rule:

Read-only tools can be used autonomously.

Action tools require human approval.

Architecture:

```text
READ OPERATIONS

AI
 │
 ├── Metrics
 ├── Logs
 ├── Health
 └── Git History


ACTION OPERATIONS

AI
 │
 ▼
Recommendation
 │
 ▼
Human Approval
 │
 ▼
MCP Action Tool
 │
 ▼
Restart / Rollback
```

---

# 8. LangGraph Architecture

LangGraph is the core workflow engine.

Do not use LangGraph simply because it is part of the technology list.

The workflow must genuinely require:

* State
* Conditional routing
* Loops
* Interruptions
* Resume capability

---

## Main Graph

```text
                         START
                           │
                           ▼
                  Understand Incident
                           │
                           ▼
                   Initial Assessment
                           │
                           ▼
                Gather Initial Evidence
                           │
              ┌────────────┼─────────────┐
              ▼            ▼             ▼
           Metrics       Logs       Git Changes
              │            │             │
              └────────────┼─────────────┘
                           │
                           ▼
                  Generate Hypotheses
                           │
                           ▼
                  Select Investigation
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
       DB Hypothesis   Resource      Deployment
                       Hypothesis    Hypothesis
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                  Evaluate Evidence
                           │
                  ┌────────┴─────────┐
                  │                  │
             Enough Evidence?       No
                  │                  │
                 YES                 │
                  │                  │
                  ▼                  │
             Root Cause              │
                  │                  │
                  ▼                  │
          Remediation Plan ◄─────────┘
                  │
                  ▼
          Human Approval Required
                  │
             ┌────┴─────┐
             │          │
          Approved    Rejected
             │          │
             ▼          ▼
        Execute       Continue
        Action       Investigation
             │
             ▼
        Validate System
             │
             ▼
            END
```

---

# 9. LangGraph State

The workflow needs shared state.

Example:

```python
class IncidentState(TypedDict):
    incident_id: str
    incident_description: str

    service_name: str

    health_status: dict
    metrics: dict
    logs: list
    git_changes: list

    hypotheses: list

    investigation_results: list

    root_cause: str
    confidence: float

    remediation_plan: dict

    human_approved: bool

    execution_result: dict
```

---

# 10. Important Learning: State vs LLM Memory

Understand the difference.

LangGraph state is not the same as LLM memory.

State represents structured workflow data.

Example:

```text
State

{
  metrics: {...},
  logs: [...],
  hypotheses: [...],
  root_cause: ...
}
```

The LLM receives only relevant portions of state depending on the node.

This is important because production agent systems should not blindly put the entire conversation and all data into every LLM prompt.

---

# 11. LangGraph Nodes

Each node should have a clear responsibility.

Do not create unnecessary agents.

---

## Node 1: Understand Incident

Input:

```text
Investigate performance degradation in Order Service.
```

Output:

```json
{
  "service": "order-service",
  "incident_type": "performance_degradation",
  "priority": "high"
}
```

This uses an LLM with structured output.

---

## Node 2: Gather Initial Evidence

This is mostly deterministic.

Call MCP tools:

```text
get_application_health()

get_service_metrics()

get_recent_errors()
```

Important learning:

Not every workflow node requires an LLM.

Use deterministic code when the operation is deterministic.

---

## Node 3: Generate Hypotheses

Use LLM reasoning.

Input:

```text
Metrics
+
Logs
+
Incident Description
```

Output:

```json
{
  "hypotheses": [
    {
      "description": "Database connection pool exhaustion",
      "confidence": 0.45,
      "investigation": "Check database timeout errors"
    },
    {
      "description": "Recent deployment regression",
      "confidence": 0.35,
      "investigation": "Inspect recent code changes"
    },
    {
      "description": "Resource exhaustion",
      "confidence": 0.20,
      "investigation": "Check CPU and memory metrics"
    }
  ]
}
```

---

## Node 4: Investigation

The agent gathers additional evidence.

Example:

For database hypothesis:

```text
get_recent_errors()
```

For deployment hypothesis:

```text
get_recent_commits()

get_changed_files()
```

For resource hypothesis:

```text
get_service_metrics()
```

---

## Node 5: Evaluate Evidence

Input:

```text
Hypotheses
+
Investigation Results
```

Output:

```json
{
  "root_cause": "Connection pool configuration regression",
  "confidence": 0.91,
  "evidence": [
    "Database timeout errors increased",
    "Latency increased after deployment",
    "Database configuration changed"
  ]
}
```

---

## Node 6: Remediation Planner

Generate recommendation.

Example:

```json
{
  "action": "ROLLBACK",
  "reason": "Deployment introduced severe performance regression",
  "risk": "MEDIUM",
  "requires_human_approval": true
}
```

---

## Node 7: Human Approval

This should demonstrate LangGraph interrupt capability.

The workflow pauses.

Example:

```text
Agent Recommendation

Rollback Order Service to previous version.

Reason:
Error rate: 12.4%
Threshold: 2%

Root Cause Confidence:
91%

Approve?
```

The user can:

```text
APPROVE

or

REJECT
```

The graph then resumes.

---

## Node 8: Execute Remediation

Call the remediation MCP.

Example:

```text
rollback_version()
```

---

## Node 9: Validate

After remediation:

```text
get_application_health()

get_service_metrics()
```

Compare before and after.

Example:

```text
Before rollback:

Error Rate: 12%
P95 Latency: 2400ms


After rollback:

Error Rate: 0.2%
P95 Latency: 130ms
```

Final result:

```text
INCIDENT RESOLVED

Root Cause:
Deployment regression

Action:
Rollback

Validation:
System metrics returned to normal
```

---

# 12. Fault Injection

The demo application must have realistic failure scenarios.

Do not randomly return fake JSON.

Create controlled fault injection.

---

## Scenario 1: Healthy

Normal service.

```text
Error Rate: < 1%

P95 Latency: < 200ms

Health: UP
```

---

## Scenario 2: Latency Regression

Introduce artificial latency.

Example:

```java
Thread.sleep(2000);
```

Metrics should reflect:

```text
P95 latency increase
```

---

## Scenario 3: Error Regression

Introduce intermittent failure.

Example:

```text
20% requests throw exception
```

Metrics:

```text
Error rate increases
```

Logs:

```text
ERROR Request processing failed
```

---

## Scenario 4: Deployment Regression

Create a separate Git commit.

The incident investigation should correlate:

```text
Deployment Time
        │
        ▼
Metric Degradation
        │
        ▼
Recent Code Change
```

This makes GitHub MCP genuinely useful.

---

# 13. Spring Boot Application

Create a simple application:

## Order Service

Endpoints:

```text
POST /orders

GET /orders/{id}

GET /orders
```

No database is required for the POC.

Use an in-memory store.

Focus should remain on AI orchestration.

---

## Required Dependencies

```text
Spring Web

Spring Boot Actuator

Micrometer Prometheus Registry
```

Expose:

```text
/actuator/health

/actuator/prometheus
```

---

# 14. Prometheus Setup

Prometheus should scrape the Spring Boot application.

Architecture:

```text
Spring Boot
     │
     │ /actuator/prometheus
     ▼
Prometheus
     │
     ▼
Observability MCP
     │
     ▼
AI Agent
```

Useful metrics:

```text
HTTP Request Count

HTTP Error Rate

HTTP Latency

JVM Memory

CPU Usage
```

---

# 15. LangChain Responsibilities

LangChain should be used for:

```text
LLM initialization

Prompt templates

Structured output

Tool integration

Message abstractions
```

Avoid hiding all logic behind an agent executor.

The POC should clearly show:

```text
LangChain
    =
LLM interaction layer


LangGraph
    =
Workflow orchestration layer
```

---

# 16. LangSmith Responsibilities

LangSmith must trace:

```text
User Request

↓

LangGraph Nodes

↓

LLM Calls

↓

MCP Tool Calls

↓

Structured Outputs

↓

Final Decision
```

During the demo, inspect:

* Graph execution path
* Tool calls
* LLM prompts
* LLM outputs
* Latency
* Token usage
* Failures

Learning objective:

Understand why traditional application logging is insufficient for AI agent systems.

---

# 17. Project Structure

```text
agentic-devops-poc/

│
├── README.md
│
├── PLAN.md
│
├── docker-compose.yml
│
├── demo-service/
│   │
│   ├── src/
│   │   └── main/
│   │
│   ├── pom.xml
│   └── Dockerfile
│
├── ai-agent/
│   │
│   ├── requirements.txt
│   │
│   ├── main.py
│   │
│   ├── graph/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── routes.py
│   │
│   ├── nodes/
│   │   ├── understand_incident.py
│   │   ├── gather_evidence.py
│   │   ├── generate_hypotheses.py
│   │   ├── investigate.py
│   │   ├── evaluate_evidence.py
│   │   ├── remediation.py
│   │   └── validate.py
│   │
│   ├── mcp/
│   │   ├── client.py
│   │   └── tools.py
│   │
│   └── prompts/
│       ├── incident_analysis.md
│       ├── hypothesis_generation.md
│       └── root_cause_analysis.md
│
├── mcp-servers/
│   │
│   ├── observability-server/
│   │
│   └── remediation-server/
│
├── prometheus/
│   │
│   └── prometheus.yml
│
├── scripts/
│   │
│   ├── generate_load.py
│   ├── inject_latency.sh
│   └── inject_failure.sh
│
└── docs/
    │
    ├── architecture.md
    ├── learning-notes.md
    └── demo-script.md
```

---

# 18. Docker Architecture

Use Docker Compose.

Services:

```text
docker-compose

├── order-service
│
├── prometheus
│
├── observability-mcp
│
├── remediation-mcp
│
└── ai-agent
```

The AI agent can initially run outside Docker during development.

Containerize only if time permits.

Do not spend hours debugging container networking.

---

# 19. Development Strategy

The project must be developed incrementally.

Never build everything at once.

Follow this sequence.

---

# PHASE 1 — Understand the Individual Technologies

Before building the complete system, create small examples.

---

## Step 1: Basic LangChain Example

Goal:

Understand LLM interaction.

Build:

```text
Input

↓

Prompt

↓

LLM

↓

Structured JSON Output
```

Example:

Input:

```text
Order service latency is 3000ms.
```

Output:

```json
{
  "severity": "HIGH",
  "issue": "Performance degradation"
}
```

Learning questions:

* What does LangChain abstract?
* What can be done directly with the model SDK?
* Why use structured output?

---

## Step 2: Basic LangGraph Example

Goal:

Understand graph execution.

Create:

```text
START

↓

Analyze

↓

Healthy?
│
├── YES → END
│
└── NO → Investigate → END
```

Learning questions:

* What is a node?
* What is an edge?
* What is conditional routing?
* What is graph state?

---

## Step 3: Basic MCP Example

Goal:

Understand MCP independently.

Create a tiny MCP server.

Tool:

```text
get_current_time()
```

Then connect an MCP client.

Architecture:

```text
Python Client

↓

MCP Protocol

↓

MCP Server

↓

Tool
```

Do this before integrating with LangGraph.

Learning questions:

* How are tools advertised?
* How does the client discover tools?
* How are arguments passed?
* How are results returned?
* What transport is being used?

---

## Step 4: LangSmith

Enable tracing on the previous examples.

Understand:

```text
Trace

Run

Span

Inputs

Outputs

Metadata
```

Only after understanding individual technologies should integration begin.

---

# PHASE 2 — Build Real Infrastructure

---

## Step 5: Spring Boot Application

Build Order Service.

Verify:

```text
Application starts

GET APIs work

Actuator works

Prometheus endpoint works
```

---

## Step 6: Prometheus

Configure scraping.

Verify metrics manually.

Important:

Do not integrate AI yet.

First confirm:

```text
Spring Boot

↓

Prometheus

↓

Metrics Query

↓

Correct Result
```

---

# PHASE 3 — Build MCP Integrations

---

## Step 7: Observability MCP

Create tools:

```text
get_application_health()

get_service_metrics()

get_recent_errors()
```

Verify manually.

Example:

```text
MCP Client

↓

get_service_metrics()

↓

Prometheus

↓

Result
```

---

## Step 8: GitHub MCP

Connect to personal GitHub repository.

Verify:

```text
get_recent_commits()

get_changed_files()
```

---

## Step 9: Remediation MCP

Implement only one action initially.

```text
restart_service()
```

Or:

```text
rollback_version()
```

Do not connect it to the agent automatically yet.

Test manually.

---

# PHASE 4 — Build Agent Workflow

---

## Step 10: Incident Understanding

Input:

```text
Investigate Order Service performance degradation.
```

Output:

```json
{
  "service": "order-service",
  "incident_type": "performance"
}
```

---

## Step 11: Evidence Gathering

Connect MCP tools.

State becomes:

```text
Incident

+

Metrics

+

Logs

+

Git Changes
```

---

## Step 12: Hypothesis Generation

Use structured output.

Do not allow free-form unstructured responses.

---

## Step 13: Investigation Loop

Implement conditional routing.

Example:

```text
Hypothesis confidence < threshold

↓

Gather More Evidence

↓

Evaluate Again
```

This is one of the main reasons to use LangGraph.

---

## Step 14: Root Cause

Generate final RCA.

---

## Step 15: Remediation

Generate action plan.

---

## Step 16: Human Approval

Implement LangGraph interrupt.

Pause execution.

Resume based on approval.

---

## Step 17: Validation

After remediation:

```text
Get Metrics Again

↓

Compare Before / After

↓

Determine Resolution
```

---

# 20. Three-Day Implementation Plan

## DAY 1 — Foundations

### Morning

Learn and prototype:

```text
LangChain

LangGraph

MCP

LangSmith
```

Each as a tiny isolated example.

### Afternoon

Build:

```text
Spring Boot App

+

Actuator

+

Prometheus
```

Success criteria:

```text
Real application metrics visible in Prometheus.
```

---

## DAY 2 — MCP Integration

### Morning

Implement:

```text
Observability MCP

GitHub MCP integration
```

Success criteria:

```text
Python client can retrieve:

Metrics

Logs

Git changes
```

### Afternoon

Connect:

```text
MCP

↓

LangGraph
```

Build:

```text
Incident

↓

Evidence Gathering

↓

Hypothesis Generation

↓

Root Cause
```

Success criteria:

```text
Agent investigates a real failure.
```

---

## DAY 3 — Agentic Workflow

### Morning

Implement:

```text
Conditional routing

Investigation loop

Remediation planning
```

### Afternoon

Implement:

```text
Human approval

Remediation

Validation

LangSmith tracing
```

Prepare demo scenarios.

---

# 21. Demo Scenarios

## Scenario 1 — Healthy

Input:

```text
Investigate Order Service.
```

Agent concludes:

```text
No significant incident detected.
```

---

## Scenario 2 — Performance Issue

Inject latency.

Agent:

```text
Detects latency increase

↓

Checks metrics

↓

Checks logs

↓

Generates hypotheses

↓

Identifies probable cause
```

---

## Scenario 3 — Deployment Regression

This should be the primary demo.

```text
Deploy Broken Version

↓

Generate Traffic

↓

Metrics Degrade

↓

User Reports Incident

↓

AI Investigates

↓

Checks Runtime Metrics

↓

Checks Logs

↓

Checks Git Changes

↓

Correlates Evidence

↓

Root Cause

↓

Recommend Rollback

↓

Human Approval

↓

Rollback

↓

Validate Metrics
```

---

# 22. Key Architectural Principles

## Principle 1: Do Not Use LLMs for Everything

Bad:

```text
LLM:
Should I call Prometheus?
```

Better:

```text
Deterministic workflow gathers baseline evidence.

LLM reasons about ambiguous evidence.
```

Use LLMs where reasoning is valuable.

Use normal code where behavior is deterministic.

---

## Principle 2: MCP Is an Integration Boundary

Do not treat MCP as just another function call.

Think:

```text
Agent Capability

↓

MCP Contract

↓

Implementation
```

The implementation can change without changing the agent.

---

## Principle 3: Actions Require More Control Than Reads

```text
READ

Metrics
Logs
Git

→ Autonomous


WRITE

Restart
Rollback
Scale

→ Human Approval
```

---

## Principle 4: LangGraph Is for Workflow

Do not create a graph just to call one LLM.

Use LangGraph because the workflow contains:

```text
State

Conditional Decisions

Loops

Interruptions

Resume
```

---

## Principle 5: Every AI Decision Should Be Observable

LangSmith should allow investigation of:

```text
Why did the agent conclude this?

Which tools were called?

What evidence was available?

Which path did the graph take?

How expensive was execution?

Where did failures occur?
```

---

# 23. Evaluation Criteria

At the end of the POC, answer these questions.

## LangChain

* Did it simplify model interaction?
* Was structured output useful?
* Was it useful for tool integration?

---

## LangGraph

* Was graph-based orchestration beneficial?
* Was state management useful?
* Were loops and conditional routing necessary?
* How easy was human interruption?

---

## MCP

* Was integration simpler?
* Can tools be reused by other agents?
* Can implementations be swapped?
* What are the security considerations?

---

## LangSmith

* Did tracing help debugging?
* Could we understand agent decisions?
* Could we evaluate agent quality?
* What production observability capabilities are available?

---

# 24. Future Extensions

Do not implement unless core POC is complete.

Possible extensions:

```text
Kubernetes

AWS CloudWatch

AWS MCP Servers

Datadog

Grafana

Slack Incident Notifications

Jira Incident Creation

RAG-based Runbooks

Multi-Agent Investigation

Automatic Canary Deployment

Policy Engine

Role-Based Access Control

Production Authentication
```

---

# 25. Definition of Success

The POC is successful if the following demo works:

```text
1. Start Spring Boot application

2. Start Prometheus

3. Inject controlled failure

4. Generate traffic

5. Metrics degrade

6. Submit incident to AI Agent

7. LangGraph starts investigation

8. Agent calls MCP tools

9. Agent gathers:
   - Metrics
   - Logs
   - Git Changes

10. Agent generates hypotheses

11. Agent evaluates evidence

12. Agent determines probable root cause

13. Agent generates remediation plan

14. LangGraph pauses for human approval

15. Human approves

16. Remediation MCP executes action

17. Agent validates system recovery

18. LangSmith displays full trace
```

If all 18 steps work, the POC successfully demonstrates a realistic Agentic DevOps workflow.

---

# 26. Final Architectural Summary

```text
┌───────────────────────────────────────────────┐
│                  USER                         │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
              INCIDENT REQUEST
                        │
                        ▼
┌───────────────────────────────────────────────┐
│                 LANGGRAPH                     │
│                                               │
│  Understand → Investigate → Decide → Act      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
                    MCP LAYER
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
   GitHub MCP    Observability MCP   Action MCP
        │               │                │
        ▼               ▼                ▼
      GitHub       Prometheus        Docker
                        │                │
                        ▼                │
                 Spring Boot ◄───────────┘
                 Application

                        │
                        ▼

                  LANGSMITH

          Trace • Debug • Evaluate
```

---

# Final Development Instruction

Build this project incrementally.

At every step:

1. Explain the architecture before implementing.
2. Explain why the technology is being used.
3. Explain alternatives.
4. Implement the smallest working version.
5. Test it independently.
6. Only then integrate it into the larger system.
7. Avoid unnecessary abstractions.
8. Prefer real integrations over mocked data where feasible.
9. Keep the project reproducible using personal/open-source infrastructure.
10. Document learnings and tradeoffs throughout development.

The goal is not simply to produce working code.

The goal is to understand how a production-style Agentic AI system can interact safely with traditional enterprise applications and infrastructure.
