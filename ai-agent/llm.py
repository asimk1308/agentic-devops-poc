"""
🧒 For a kid: this file is a phone with two buttons. Button 1 calls a
big, very smart AI brain that lives on the internet (Claude). Button 2
calls a smaller AI brain that lives right here on this computer
(Ollama). Every part of the detective that needs to "think" picks up
THIS phone instead of having its own -- so if we ever want to switch
brains, we only change it in one place.

Single place every LLM-calling node gets its chat model from (Section 15
-- LangChain's job is "LLM initialization," among other things). Nodes
import get_llm() instead of constructing ChatAnthropic/ChatOllama
directly, so switching providers is one env var here instead of editing
four node files -- a small, concrete answer to Section 23's own
evaluation question ("did LangChain simplify model interaction?").

LLM_PROVIDER=anthropic (default): needs ANTHROPIC_API_KEY, a funded
  workspace. Best structured-output reliability of the two.
LLM_PROVIDER=ollama: needs a local `ollama serve` running with
  OLLAMA_MODEL pulled (default: qwen2.5). No API key, no cost, runs
  entirely on-machine -- see docs/learning-notes.md Phase 4 for how its
  structured-output compliance compares to Claude's on this exact graph
  (weaker on free-text enum hints, which is why the four Pydantic models
  in nodes/ use `Literal` fields rather than relying on the description
  string alone).
"""
import os


def get_llm(temperature: float = 0):
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5"), temperature=temperature)

    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"), temperature=temperature)
