"""
Shared fixtures for the fast, mocked/deterministic test suite (tests/unit/).

The `fake_llm` fixture formalizes the manual monkeypatching described in
docs/learning-notes.md's Phase 4 section: every LLM node follows the same
`get_llm().with_structured_output(Model)` then `(prompt | structured).invoke(...)`
shape, so one fake stands in for all four -- it ignores the rendered
prompt and returns a fixed Pydantic instance, so tests assert on each
node's state-shaping logic (not on model behavior, which belongs in
tests/evals/).
"""
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from dotenv import load_dotenv
from langchain_core.runnables import Runnable

# Same .env main.py loads before importing graph.graph -- needed here so
# tests/evals/ (LLM_PROVIDER, ANTHROPIC_API_KEY) sees the same config a
# real `python main.py` run would, without pytest needing its own copy.
load_dotenv(Path(__file__).parent.parent / ".env")

MCP_SERVERS_DIR = Path(__file__).parent.parent.parent / "mcp-servers"


def load_mcp_server_module(name: str, relative_path: str) -> ModuleType:
    """
    Import an MCP server's server.py by file path under a unique module
    name (not plain "server") so tests/unit/test_observability_server.py
    and tests/unit/test_remediation_server.py -- each importing a
    same-named server.py from a different directory -- don't collide in
    sys.modules. The tool functions inside stay ordinary, directly
    callable Python functions: MCPServer.tool() registers and returns fn
    unchanged (see mcp.server.mcpserver.MCPServer.tool), so calling them
    here never spins up the real MCP stdio transport.
    """
    path = MCP_SERVERS_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeStructuredLLM(Runnable):
    """Stands in for get_llm().with_structured_output(Model) -- a Runnable
    (so `prompt | this` builds a real RunnableSequence) whose .invoke()
    ignores its input and always returns the canned response."""

    def __init__(self, response: Any):
        self._response = response

    def invoke(self, input: Any = None, config: Any = None, **kwargs: Any) -> Any:
        return self._response


class _FakeLLM:
    def __init__(self, response: Any):
        self._response = response

    def with_structured_output(self, _model: Any) -> _FakeStructuredLLM:
        return _FakeStructuredLLM(self._response)


@pytest.fixture
def fake_llm():
    """
    fake_llm(node_module, response) monkeypatches node_module.get_llm so
    the node's LLM call returns `response` (a Pydantic instance matching
    whatever the node's with_structured_output(Model) expects) instead of
    calling a real model. Returns nothing; call it once per test.
    """

    def _install(monkeypatch: pytest.MonkeyPatch, node_module: Any, response: Any) -> None:
        monkeypatch.setattr(node_module, "get_llm", lambda *a, **k: _FakeLLM(response))

    return _install
