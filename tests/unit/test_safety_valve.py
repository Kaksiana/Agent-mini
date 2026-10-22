"""TC-L1-016/TC-L1-029：Runtime 循环安全阀。"""

import asyncio

import pytest

from agent_mini.llm import models as llm_models
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.loop import LoopPolicy, ToolOutcome

pytestmark = pytest.mark.unit

TOOL = llm_models.ToolSchema(
    name="echo",
    description="回显",
    parameters={"type": "object", "properties": {}},
)
MAX_STEPS_MESSAGE = "已达到最大步数限制，已停止。"
DEADLINE_MESSAGE = "已达到截止时间限制，已停止。"
REPEAT_MESSAGE = "检测到重复工具调用，已停止。"


class ScriptedLLM:
    def __init__(self, responses: list[llm_models.LLMResponse]) -> None:
        self.responses = responses
        self.requests = 0
        self.last_messages: list[llm_models.Message] = []

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        self.requests += 1
        self.last_messages = messages
        return self.responses.pop(0)


class Executor:
    def schemas(self) -> list[llm_models.ToolSchema]:
        return [TOOL]

    async def execute(self, call: llm_models.ToolCall) -> ToolOutcome:
        return ToolOutcome(ok=True, content="ok")


class SlowExecutor(Executor):
    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled = False

    async def execute(self, call: llm_models.ToolCall) -> ToolOutcome:
        self.started.append(call.id)
        try:
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return ToolOutcome(ok=True, content="late")


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


def _call(call_id: str = "call_1", text: str = "hi") -> llm_models.ToolCall:
    return llm_models.ToolCall(id=call_id, name="echo", arguments={"text": text})


async def test_max_steps_stops_exactly_at_limit() -> None:
    llm = ScriptedLLM([_response(calls=[_call()]) for _ in range(5)])
    executor = Executor()
    policy = LoopPolicy(max_steps=3, repeat_threshold=10)

    result = await Agent(llm, executor, policy).run("hi")

    assert result.steps == 3
    assert result.truncated is True
    assert result.termination_reason == "max_steps"
    assert result.reply == MAX_STEPS_MESSAGE
    assert llm.requests == 3


async def test_deadline_cancels_hanging_tool_and_fills_batch() -> None:
    first = _call("call_1")
    second = _call("call_2")
    llm = ScriptedLLM([_response(calls=[first, second])])
    executor = SlowExecutor()
    policy = LoopPolicy(deadline_seconds=0.01)

    result = await Agent(llm, executor, policy).run("hi")

    assert result.steps == 1
    assert result.truncated is True
    assert result.termination_reason == "deadline"
    assert result.reply == DEADLINE_MESSAGE
    assert executor.started == ["call_1"]
    assert executor.cancelled is True
    assert len(result.tool_traces) == 2
    assert [trace.error_code for trace in result.tool_traces] == [
        "deadline",
        "deadline",
    ]
    tool_messages = [message for message in llm.last_messages if message.role == "tool"]
    assert [message.tool_call_id for message in tool_messages] == ["call_1", "call_2"]


async def test_repeat_same_call_stops_at_threshold() -> None:
    call = _call()
    llm = ScriptedLLM([_response(calls=[call]) for _ in range(5)])
    executor = Executor()
    policy = LoopPolicy(max_steps=8, repeat_threshold=3)

    result = await Agent(llm, executor, policy).run("hi")

    assert result.steps == 3
    assert result.truncated is True
    assert result.termination_reason == "repeat"
    assert result.reply == REPEAT_MESSAGE
    assert result.tool_calls == 3


async def test_normal_convergence_has_no_truncation() -> None:
    llm = ScriptedLLM(
        [
            _response(calls=[_call()]),
            _response(calls=[_call()]),
            _response(content="完成"),
        ]
    )
    executor = Executor()
    policy = LoopPolicy(max_steps=8, repeat_threshold=3)

    result = await Agent(llm, executor, policy).run("hi")

    assert result.steps == 3
    assert result.truncated is False
    assert result.termination_reason is None
    assert result.reply == "完成"
