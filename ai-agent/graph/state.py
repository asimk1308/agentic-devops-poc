"""
Shared LangGraph state (Spec Section 9).

Section 10 is the important distinction to keep in mind while reading
this: this TypedDict is structured *workflow* data, not LLM conversation
memory. Nodes read whatever subset of it they need and write back a
partial update -- LangGraph merges each returned key into the running
state (last write wins per key; there's no reducer here beyond that,
since nothing in this graph needs to *accumulate* a key across visits
except investigation_results/investigation_loops, which nodes update by
reading the current value and returning the extended one explicitly).

total=False: only incident_id/incident_description/service_name exist at
graph start; every other key is populated progressively as nodes run.
"""
from typing import TypedDict


class IncidentState(TypedDict, total=False):
    # Set at graph invocation (main.py)
    incident_id: str
    incident_description: str

    # Node 1 -- understand_incident
    service_name: str
    incident_type: str
    priority: str

    # Node 2 -- gather_evidence (initial pass)
    health_status: dict
    metrics: dict
    logs: dict
    git_changes: dict

    # Node 3 -- generate_hypotheses
    hypotheses: list

    # Node 4 -- investigate (loop-accumulated)
    investigation_results: list
    investigation_loops: int

    # Node 5 -- evaluate_evidence
    root_cause: str
    confidence: float
    evidence: list

    # Node 6 -- remediation planner
    remediation_plan: dict

    # Node 7 -- human approval (set via Command(resume=...))
    human_approved: bool

    # Node 8 -- execute_remediation
    execution_result: dict

    # Node 9 -- validate
    validation: dict
    final_summary: str
