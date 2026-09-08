"""
Step 4 — LangSmith.

Goal: understand what LangSmith adds once you enable tracing on a chain
like Step 1's — Trace, Run, Span, Inputs, Outputs, Metadata — and why
that's not the same thing as normal application logging (a log line tells
you *that* something happened; a trace tells you the exact prompt, the
exact raw model output, and the exact token cost of *why*).

Tracing is enabled purely through environment variables — no code change
to the chain itself is required:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=<your langsmith key>
    LANGCHAIN_PROJECT=<project name to group runs under>

Run:
    ai-agent/.venv/bin/python ai-agent/step4_langsmith_tracing.py
"""
import os

from dotenv import load_dotenv

load_dotenv()

TRACING_ON = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
HAS_LANGSMITH_KEY = bool(os.getenv("LANGCHAIN_API_KEY"))
PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
LLM_READY = PROVIDER == "ollama" or bool(os.getenv("ANTHROPIC_API_KEY"))
PROJECT = os.getenv("LANGCHAIN_PROJECT", "agentic-devops-poc")


def explain_what_tracing_gives_you() -> None:
    print(
        "LangSmith concepts:\n"
        "  Trace    - one end-to-end execution (here: one chain.invoke() call)\n"
        "  Run      - one step inside a trace (a prompt render, an LLM call,\n"
        "             a tool call) -- traces are trees of runs\n"
        "  Span     - the timing/duration wrapper around a run\n"
        "  Inputs   - exactly what was sent to that run (e.g. the rendered\n"
        "             prompt messages, not just your raw input string)\n"
        "  Outputs  - exactly what came back (e.g. the raw model output,\n"
        "             before it was parsed into IncidentAssessment)\n"
        "  Metadata - token usage, latency, model name, tags\n"
    )


def main() -> None:
    explain_what_tracing_gives_you()

    if not (TRACING_ON and HAS_LANGSMITH_KEY):
        print(
            "Tracing is NOT active right now (LANGCHAIN_TRACING_V2 / "
            "LANGCHAIN_API_KEY unset in ai-agent/.env).\n\n"
            "If it were active, running step1_langchain_basics.py would "
            "silently create a trace at https://smith.langchain.com under "
            f"the '{PROJECT}' project, containing:\n"
            "  - a top-level Run for the chain (prompt | structured_model)\n"
            "  - a child Run for the chat model call (get_llm() in\n"
            "    ai-agent/llm.py), with the exact rendered prompt, the raw\n"
            "    model response, and token counts\n"
            "  - a child Run for the structured-output parsing step\n\n"
            "To turn it on: set LANGCHAIN_TRACING_V2=true and "
            "LANGCHAIN_API_KEY in ai-agent/.env, then re-run this script."
        )
        return

    if not LLM_READY:
        print(
            "Tracing is configured, but an LLM is also needed to actually "
            "run a traced chain -- ANTHROPIC_API_KEY is unset and "
            "LLM_PROVIDER isn't 'ollama'. See ai-agent/llm.py / README.md "
            "'One-time setup'."
        )
        return

    # Tracing is picked up automatically from the env vars above -- no
    # LangSmith SDK call is needed in the chain code itself. get_llm()
    # (ai-agent/llm.py, added in Phase 4) is used here too instead of a
    # hardcoded ChatAnthropic so this script also runs against
    # LLM_PROVIDER=ollama -- same reasoning as the graph nodes.
    from llm import get_llm
    from step1_langchain_basics import PROMPT, IncidentAssessment

    chain = PROMPT | get_llm().with_structured_output(IncidentAssessment)

    sample_signal = "Order service latency is 3000ms, baseline is 120ms."
    result = chain.invoke({"signal": sample_signal})

    print("Ran a traced chain. Result:", result.model_dump_json())
    print(
        f"\nOpen https://smith.langchain.com and look under the '{PROJECT}' "
        "project to see the trace this call just created."
    )


if __name__ == "__main__":
    main()
