"""
Node 1 (Spec Section 11): Understand Incident.

LLM call with structured output -- turns a free-text incident report
into the (service, incident_type, priority) shape every later node
routes and reasons on, instead of every node re-parsing English.
"""
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "incident_analysis.md"


class IncidentUnderstanding(BaseModel):
    service: str = Field(description="The service name mentioned or implied")
    incident_type: str = Field(
        description="One of: performance_degradation, error_spike, outage, unknown"
    )
    priority: str = Field(description="One of: low, medium, high, critical")


def understand_incident(state: dict) -> dict:
    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    structured = model.with_structured_output(IncidentUnderstanding)
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
