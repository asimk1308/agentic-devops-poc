"""
🧒 For a kid: Step 6. Now the detective writes down her plan for how to
fix things -- but she does NOT do anything yet. Just a piece of paper
saying "here's what I'd do, here's why, and here's how risky it is."
That paper is what gets shown to you in the next step.

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
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from llm import get_llm

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "remediation_planning.md"


class RemediationPlan(BaseModel):
    # Literal fields, not description-only strings -- routes.py and
    # nodes/human_approval.py compare `action` by exact equality
    # ("== NONE"), so this needs to be schema-enforced, not just
    # prompted for, especially on a weaker local model (llm.py).
    action: Literal["RESTART_SERVICE", "NONE"]
    reason: str
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    requires_human_approval: bool


def plan_remediation(state: dict) -> dict:
    structured = get_llm().with_structured_output(RemediationPlan)
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
