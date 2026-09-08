"""
Node 5 (Spec Section 11): Evaluate Evidence.

LLM reasoning over hypotheses + whatever investigate() has gathered so
far. Structured output again, for the same reason as Node 3: routes.py
needs to read `confidence` as a number to decide whether to loop back
for another investigation pass (Step 13's conditional routing) or move
on to remediation planning -- it can't do that off free text.
"""
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "root_cause_analysis.md"


class RootCauseAnalysis(BaseModel):
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


def evaluate_evidence(state: dict) -> dict:
    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    structured = model.with_structured_output(RootCauseAnalysis)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PROMPT_PATH.read_text()),
            (
                "human",
                "Hypotheses: {hypotheses}\n\n"
                "Investigation results: {investigation_results}",
            ),
        ]
    )
    result: RootCauseAnalysis = (prompt | structured).invoke(
        {
            "hypotheses": json.dumps(state.get("hypotheses", [])),
            "investigation_results": json.dumps(state.get("investigation_results", [])),
        }
    )

    return {
        "root_cause": result.root_cause,
        "confidence": result.confidence,
        "evidence": result.evidence,
    }
