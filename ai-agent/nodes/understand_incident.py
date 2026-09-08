"""
Node 1 (Spec Section 11): Understand Incident.

LLM call with structured output -- turns a free-text incident report
into the (service, incident_type, priority) shape every later node
routes and reasons on, instead of every node re-parsing English.
"""
from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm import get_llm

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "incident_analysis.md"


class IncidentUnderstanding(BaseModel):
    service: str = Field(description="The service name mentioned or implied")
    # Literal, not just a description string, so the model's structured-
    # output schema itself constrains the value to these four -- a
    # weaker local model (see llm.py, LLM_PROVIDER=ollama) won't reliably
    # honor an enum stated only in prose, but does honor an actual JSON
    # schema enum. See docs/learning-notes.md Phase 4 for what qwen2.5
    # returned before vs. after this change.
    incident_type: Literal["performance_degradation", "error_spike", "outage", "unknown"]
    priority: Literal["low", "medium", "high", "critical"]


def understand_incident(state: dict) -> dict:
    structured = get_llm().with_structured_output(IncidentUnderstanding)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PROMPT_PATH.read_text()),
            ("human", "{incident_description}"),
        ]
    )
    result: IncidentUnderstanding = (prompt | structured).invoke(
        {"incident_description": state["incident_description"]}
    )

    return {
        "service_name": result.service,
        "incident_type": result.incident_type,
        "priority": result.priority,
    }
