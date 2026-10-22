"""S04 TC：ReAct 工具循环、轨迹与配对。"""

import json
from typing import Any

import pytest

from agent_mini.llm import models as llm_models
from agent_mini.llm.errors import LLMProtocolError
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.loop import ToolOutcome

pytestmark = pytest.mark.unit

TOOL = llm_models.ToolSchema(
    name="echo",
    description="回显",
    parameters={"type": "object", "properties": {"text": {"type": "string"}}},
)


class FakeExecutor:
    """最小工具执行器替身。"""

    def __init__(self) -> None:
        self.calls: list[llm_models.ToolCall] = []

    def schemas(self) -> list[llm_models.ToolSchema]:
        return [TOOL]

    async def execute(self, call: llm_models.ToolCall) -> ToolOutcome:
        self.calls.append(call)
        if call.name == "unknown":
            return _outcome(False, "未知工具", "unknown_tool")
        return _outcome(True, f"echo:{call.arguments}")


class ScriptedLLM:
    """按脚本返回响应并记录请求。"""

    def __init__(self, responses: list[llm_models.LLMResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[list[llm_models.Message], object]] = []

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        self.requests.append((list(messages), tools))
        return self.responses.pop(0)


def _outcome(ok: bool, content: str, error_code: str | None = None) -> ToolOutcome:
    return ToolOutcome(ok=ok, content=content, error_code=error_code)


def _tool_call(
    call_id: str,
    name: str = "echo",
    args: dict[str, Any] | None = None,
) -> llm_models.ToolCall:
    return llm_models.ToolCall(id=call_id, name=name, arguments=args or {"text": "hi"})


def _response(
    *,
    content: str | None = None,
    calls: list[llm_models.ToolCall] | None = None,
    reasoning: str | None = None,
    finish_reason: str = "stop",
) -> llm_models.LLMResponse:
    usage = llm_models.Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    return llm_models.LLMResponse(
        content=content,
        tool_calls=calls or [],
        reasoning_content=reasoning,
        finish_reason=finish_reason,
        usage=usage,
    )


async def test_two_step_tool_loop_pairs_messages() -> None:
    call = _tool_call("call_1")
    llm = ScriptedLLM(
        [
            _response(calls=[call], finish_reason="tool_calls"),
            _response(content="完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert result.reply == "完成"
    assert result.steps == 2
    assert result.tool_calls == 1
    assert result.usage.total_tokens == 4
    assert len(result.trace) == 2
    assert result.trace[0].decision == "tool_call"
    assert result.trace[1].decision == "final"
    assert result.tool_traces[0].call_id == "call_1"
    assert set(type(result.trace[0]).model_fields) == {
        "step",
        "decision",
        "thought",
        "thought_source",
        "reasoning_present",
        "tool_calls",
        "error_code",
    }
    assert set(type(result.tool_traces[0]).model_fields) == {
        "call_id",
        "tool",
        "args",
        "ok",
        "error_code",
        "observation",
    }
    second_messages = llm.requests[1][0]
    assert [message.role for message in second_messages] == ["user", "assistant", "tool"]
    assert second_messages[1].tool_calls is not None
    assert second_messages[1].tool_calls[0].id == "call_1"
    assert second_messages[2].tool_call_id == "call_1"
    assert executor.calls == [call]


async def test_three_steps_converge() -> None:
    llm = ScriptedLLM(
        [
            _response(calls=[_tool_call("call_1")], finish_reason="tool_calls"),
            _response(calls=[_tool_call("call_2")], finish_reason="tool_calls"),
            _response(content="三步完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert result.reply == "三步完成"
    assert result.steps == 3
    assert result.tool_calls == 2
    assert [item.decision for item in result.trace] == [
        "tool_call",
        "tool_call",
        "final",
    ]


async def test_content_with_multiple_tools_preserves_order() -> None:
    calls = [_tool_call("call_1"), _tool_call("call_2")]
    llm = ScriptedLLM(
        [
            _response(content="先执行工具", calls=calls, finish_reason="tool_calls"),
            _response(content="完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert result.reply == "完成"
    assert result.tool_calls == 2
    assert len(result.tool_traces) == 2
    assert len(result.trace[0].tool_calls) == 2
    second_messages = llm.requests[1][0]
    assert [message.role for message in second_messages] == [
        "user",
        "assistant",
        "tool",
        "tool",
    ]
    assert [message.tool_call_id for message in second_messages[2:]] == [
        "call_1",
        "call_2",
    ]
    assert result.tool_traces[0].tool == "echo"


async def test_trace_does_not_expose_reasoning_or_final_text() -> None:
    llm = ScriptedLLM(
        [
            _response(
                calls=[_tool_call("call_1")],
                reasoning="PRIVATE_REASON",
                finish_reason="tool_calls",
            ),
            _response(content="最终答案", reasoning="PRIVATE_FINAL"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert result.trace[0].reasoning_present is True
    assert result.trace[1].reasoning_present is True
    assert result.trace[0].thought_source == "runtime_summary"
    assert "PRIVATE_REASON" not in json.dumps(result.model_dump(), ensure_ascii=False)
    assert result.trace[1].thought != "最终答案"


async def test_thinking_reasoning_is_kept_in_assistant_history() -> None:
    llm = ScriptedLLM(
        [
            _response(
                calls=[_tool_call("call_1")],
                reasoning="PRIVATE_REASON",
                finish_reason="tool_calls",
            ),
            _response(content="完成"),
        ]
    )
    executor = FakeExecutor()

    await Agent(llm, executor).run("hi")

    second_messages = llm.requests[1][0]
    assert second_messages[1].reasoning_content == "PRIVATE_REASON"
    assert second_messages[1].role == "assistant"


async def test_invalid_arguments_are_not_executed_and_are_refed() -> None:
    invalid = llm_models.ToolCall(
        id="bad_1",
        name="echo",
        arguments=None,
        error_code="invalid_arguments",
    )
    llm = ScriptedLLM(
        [
            _response(calls=[invalid], finish_reason="tool_calls"),
            _response(content="修正后完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert executor.calls == []
    assert result.tool_traces[0].error_code == "invalid_arguments"
    assert result.tool_traces[0].ok is False
    tool_message = llm.requests[1][0][2]
    assert tool_message.tool_call_id == "bad_1"
    assert "invalid_arguments" in (tool_message.content or "")


async def test_unknown_tool_error_is_refed() -> None:
    llm = ScriptedLLM(
        [
            _response(calls=[_tool_call("unknown_1", name="unknown")], finish_reason="tool_calls"),
            _response(content="完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    assert result.tool_traces[0].error_code == "unknown_tool"
    assert result.tool_traces[0].ok is False
    assert llm.requests[1][0][2].tool_call_id == "unknown_1"


async def test_sensitive_arguments_and_observation_are_redacted() -> None:
    secret = "sk-fake-secret"
    call = _tool_call("call_1", args={"api_key": secret, "text": "a" * 300})
    llm = ScriptedLLM(
        [
            _response(calls=[call], finish_reason="tool_calls"),
            _response(content="完成"),
        ]
    )
    executor = FakeExecutor()

    result = await Agent(llm, executor).run("hi")

    trace = result.tool_traces[0]
    assert trace.args["api_key"] == "***"
    assert secret not in json.dumps(result.model_dump(), ensure_ascii=False)
    assert len(trace.observation) <= 200


async def test_no_executor_rejects_tool_calls() -> None:
    llm = ScriptedLLM([_response(calls=[_tool_call("call_1")], finish_reason="tool_calls")])

    with pytest.raises(LLMProtocolError):
        await Agent(llm).run("hi")
