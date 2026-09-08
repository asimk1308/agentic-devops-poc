"""
Node 3 (Spec Section 11): Generate Hypotheses.

LLM reasoning over the initial evidence. Structured output (a list of
hypotheses, not free text) so Node 4 can iterate over them
programmatically instead of parsing prose.

Also re-entered by routes.route_after_evaluate's "investigate_more" edge
(Step 13's loop) once investigate() has produced results and
evaluate_evidence() judged confidence still too low. On that second
pass, `investigation_results` is non-empty, so it's included alongside
the original evidence -- otherwise the model would just regenerate the
same hypotheses from the same initial snapshot and the loop would never
converge. New hypotheses are merged with (not replacing) the prior list
so investigate() can still dispatch on ones it hasn't covered yet.
"""
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "hypothesis_generation.md"


class Hypothesis(BaseModel):
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    investigation: str


class Hypotheses(BaseModel):
    hypotheses: list[Hypothesis]


def generate_hypotheses(state: dict) -> dict:
    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    structured = model.with_structured_output(Hypotheses)

    human_message = (
        "Incident: {incident_description}\n\n"
        "Health status: {health_status}\n"
        "Service metrics: {metrics}\n"
        "Recent errors: {logs}"
    )
    investigation_results = state.get("investigation_results", [])
    if investigation_results:
        human_message += (
            "\n\nPrior hypotheses already proposed: {prior_hypotheses}\n"
            "Investigation results gathered so far (confidence was judged "
            "too low based on these -- propose additional or refined "
            "hypotheses, not a repeat of ones already covered): "
            "{investigation_results}"
        )

    prompt = ChatPromptTemplate.from_messages(
        [("system", PROMPT_PATH.read_text()), ("human", human_message)]
    )
    result: Hypotheses = (prompt | structured).invoke(
        {
            "incident_description": state["incident_description"],
            "health_status": json.dumps(state.get("health_status", {})),
            "metrics": json.dumps(state.get("metrics", {})),
            "logs": json.dumps(state.get("logs", {})),
            "prior_hypotheses": json.dumps(state.get("hypotheses", [])),
            "investigation_results": json.dumps(investigation_results),
        }
    )

    existing = {h["description"]: h for h in state.get("hypotheses", [])}
    for h in result.hypotheses:
        existing[h.description] = h.model_dump()

    # Highest-confidence hypothesis first -- Node 4 investigates in this order.
    ordered = sorted(existing.values(), key=lambda h: h["confidence"], reverse=True)
    return {"hypotheses": ordered}
