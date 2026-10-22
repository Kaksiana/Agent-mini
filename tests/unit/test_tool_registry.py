"""TC-L1-007/008/009：工具注册、Schema 与执行。"""

from typing import cast

import pytest
from pydantic import BaseModel

from agent_mini.llm import models as llm_models
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.tools.registry import (
    DuplicateToolError,
    ToolContext,
    ToolRegistry,
    ToolResult,
    tool,
)

pytestmark = pytest.mark.unit


class EchoArgs(BaseModel):
    text: str


def echo(text: str) -> ToolResult:
    return ToolResult(True, f"echo:{text}")


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    tool("echo", "回显", EchoArgs, registry=registry)(echo)
    return registry


def test_register_and_lookup() -> None:
    registry = _registry()

    spec = registry.get("echo")

    assert spec.name == "echo"
    assert [schema["name"] for schema in registry.schemas()] == ["echo"]


def test_pydantic_schema_matches_openai_contract() -> None:
    schema = _registry().get("echo").to_json_schema()

    parameters = cast(dict[str, object], schema["parameters"])
    properties = cast(dict[str, object], parameters["properties"])
    assert schema["name"] == "echo"
    assert schema["description"] == "回显"
    assert parameters["type"] == "object"
    assert "text" in properties
    assert parameters["required"] == ["text"]


def test_duplicate_registration_is_rejected() -> None:
    registry = _registry()

    with pytest.raises(DuplicateToolError):
        tool("echo", "另一个", EchoArgs, registry=registry)(echo)

    assert registry.get("echo").description == "回显"


async def test_invalid_arguments_do_not_execute_handler() -> None:
    registry = _registry()

    result = await registry.execute("echo", {})

    assert result.ok is False
    assert result.error_code == "invalid_arguments"


async def test_handler_exception_becomes_tool_error() -> None:
    registry = ToolRegistry()

    def broken(text: str) -> ToolResult:
        raise RuntimeError("boom")

    tool("broken", "失败", EchoArgs, registry=registry)(broken)

    result = await registry.execute("broken", {"text": "x"})

    assert result.ok is False
    assert result.error_code == "tool_execution_error"


def test_tool_result_rejects_contradictory_states() -> None:
    with pytest.raises(ValueError):
        ToolResult(True, "x", "error")
    with pytest.raises(ValueError):
        ToolResult(False, "x")


def test_tool_context_reserved() -> None:
    context = ToolContext(session_id="s", trace_id="t")

    assert context.session_id == "s"


async def test_registry_drives_runtime_without_runtime_changes() -> None:
    registry = _registry()
    executor = RegistryExecutor(registry)
    call = llm_models.ToolCall(id="call_1", name="echo", arguments={"text": "hi"})
    llm = _ScriptedLLM(
        [
            _response(calls=[call]),
            _response(content="完成"),
        ]
    )

    result = await Agent(llm, executor).run("hi")

    assert result.reply == "完成"
    assert result.tool_calls == 1
    assert result.tool_traces[0].tool == "echo"
    assert llm.tools[0].name == "echo"


class _ScriptedLLM:
    def __init__(self, responses: list[llm_models.LLMResponse]) -> None:
        self.responses = responses
        self.tools: list[llm_models.ToolSchema] = []

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        if tools:
            self.tools = tools
        return self.responses.pop(0)


def _response(
    *,
    content: str | None = None,
    calls: list[llm_models.ToolCall] | None = None,
) -> llm_models.LLMResponse:
    return llm_models.LLMResponse(
        content=content,
        tool_calls=calls or [],
        finish_reason="tool_calls" if calls else "stop",
        usage=llm_models.Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )
