"""
Step 1 — LangChain basics.

Goal: understand what LangChain actually gives you on top of calling the
Anthropic SDK directly.

  Input ("Order service latency is 3000ms.")
    -> Prompt template
    -> LLM (ChatAnthropic)
    -> Structured JSON output (enforced by a Pydantic schema)

What this demonstrates:
  - ChatPromptTemplate: separates the prompt shape from the input data.
  - ChatAnthropic: a provider-agnostic chat model interface — swapping to
    ChatOpenAI later would not change any code below this import.
  - with_structured_output(): the model is constrained to return an
    instance of IncidentAssessment, not free-form text you'd have to parse.
  - The `prompt | structured_model` syntax is LCEL (LangChain Expression
    Language): chain steps with `|` like Unix pipes.

Run:
    ai-agent/.venv/bin/python ai-agent/step1_langchain_basics.py

Learning questions to answer for yourself after running this (see
docs/learning-notes.md):
  - What does LangChain abstract away here that the raw Anthropic SDK
    would have made you write by hand?
  - What could you do directly with the model SDK instead, and what would
    you lose?
  - Why is structured output worth enforcing at the model layer instead of
    just asking the model to "reply in JSON" and parsing it yourself?
"""
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


class IncidentAssessment(BaseModel):
    """Structured judgment about a raw incident signal."""

    severity: str = Field(description="One of LOW, MEDIUM, HIGH, CRITICAL")
    issue: str = Field(description="Short human-readable description of the likely issue")


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an SRE triage assistant. Classify the signal you're given."),
        ("human", "{signal}"),
    ]
)


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY is not set.\n"
            "  1. cd ai-agent\n"
            "  2. edit .env and set ANTHROPIC_API_KEY=sk-ant-...\n"
            "  3. re-run this script.\n"
        )
        return

    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    structured_model = model.with_structured_output(IncidentAssessment)

    chain = PROMPT | structured_model

    sample_signal = "Order service latency is 3000ms, baseline is 120ms."
    result: IncidentAssessment = chain.invoke({"signal": sample_signal})

    print("Input signal:   ", sample_signal)
    print("Structured output:")
    print(" ", result.model_dump_json(indent=2).replace("\n", "\n  "))


if __name__ == "__main__":
    main()
