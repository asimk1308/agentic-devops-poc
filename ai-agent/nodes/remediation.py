"""
Node 6 (Spec Section 11): Remediation Planner.

LLM reasoning over the established root cause -- proposes an action
(the one write tool this POC has, `restart_service`, or `NONE`) plus a
human-facing justification. This node never executes anything; it only
produces the plan that Node 7 (human_approval) presents for a yes/no
decision. Keeping planning and execution as separate nodes is what makes
the human-approval interrupt sit cleanly between them (Section 22
Principle 3).
"""
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "remediation_planning.md"


class RemediationPlan(BaseModel):
    action: str = Field(description="RESTART_SERVICE or NONE")
    reason: str
    risk: str = Field(description="LOW, MEDIUM, or HIGH")
    requires_human_approval: bool


def plan_remediation(state: dict) -> dict:
    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    structured = model.with_structured_output(RemediationPlan)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PROMPT_PATH.read_text()),
            (
                "human",
                "Root cause: {root_cause}\n"
                "Confidence: {confidence}\n"
                "Evidence: {evidence}",
            ),
        ]
    )
    result: RemediationPlan = (prompt | structured).invoke(
        {
            "root_cause": state.get("root_cause", ""),
            "confidence": state.get("confidence", 0.0),
            "evidence": json.dumps(state.get("evidence", [])),
        }
    )

    return {"remediation_plan": result.model_dump()}
