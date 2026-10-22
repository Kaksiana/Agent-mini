"""TC-L1-015A/B/C：S03 单轮直答与 AgentResult。"""

import inspect

import pytest
from pydantic import ValidationError

from agent_mini.llm import models as llm_models
from agent_mini.llm.errors import LLMEmptyResponseError, LLMProtocolError, LLMTimeoutError
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.result import AgentResult

pytestmark = pytest.mark.unit


class StubLLM:
    """记录调用并返回固定响应的 LLM 替身。"""

    def __init__(self, response: llm_models.LLMResponse) -> None:
        self.response = response
        self.calls: list[tuple[list[llm_models.Message], object]] = []

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        self.calls.append((list(messages), tools))
        return self.response


class ErrorLLM:
    """抛出指定异常的 LLM 替身。"""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        self.calls += 1
        raise self.error


def _usage() -> llm_models.Usage:
    return llm_models.Usage(prompt_tokens=2, completion_tokens=1, total_tokens=3)


async def test_direct_reply_returns_one_step_result() -> None:
    usage = _usage()
    stub = StubLLM(
        llm_models.LLMResponse(
            content="答案",
            reasoning_content="私有推理",
            finish_reason="stop",
            usage=usage,
        )
    )
    agent = Agent(stub)

    result = await agent.run("你好")

    assert result.reply == "答案"
    assert result.steps == 1
    assert result.usage == usage
    assert set(type(result).model_fields) == {
        "reply",
        "steps",
        "usage",
        "trace",
        "tool_calls",
        "tool_traces",
        "truncated",
        "termination_reason",
    }
    assert len(stub.calls) == 1
    messages, tools = stub.calls[0]
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "你好"
    assert tools is None
    assert result.trace[0].decision == "final"
    assert "reasoning" not in result.reply


async def test_agent_result_is_frozen() -> None:
    result = await Agent(StubLLM(_response("答案"))).run("你好")

    with pytest.raises(ValidationError):
        result.reply = "被修改"


def test_run_signature_has_no_session_id() -> None:
    parameters = inspect.signature(Agent.run).parameters

    assert list(parameters) == ["self", "user_input"]
    assert inspect.iscoroutinefunction(Agent.run)


async def test_empty_response_error_is_propagated() -> None:
    error = LLMEmptyResponseError("模型没有返回有效答案")
    stub = ErrorLLM(error)
    agent = Agent(stub)

    with pytest.raises(LLMEmptyResponseError) as exc_info:
        await agent.run("你好")

    assert exc_info.value is error
    assert stub.calls == 1


async def test_llm_error_is_propagated_without_wrapping() -> None:
    error = LLMTimeoutError("模型调用超时（5.0 秒）")
    stub = ErrorLLM(error)
    agent = Agent(stub)

    with pytest.raises(LLMTimeoutError) as exc_info:
        await agent.run("你好")

    assert exc_info.value is error
    assert stub.calls == 1


@pytest.mark.parametrize("content", [None, "伴随文本"])
async def test_unexpected_tool_calls_are_rejected(content: str | None) -> None:
    response = llm_models.LLMResponse(
        content=content,
        finish_reason="tool_calls",
        tool_calls=[
            llm_models.ToolCall(
                id="call_1",
                name="echo",
                arguments={},
            )
        ],
        usage=_usage(),
    )
    agent = Agent(StubLLM(response))

    with pytest.raises(LLMProtocolError):
        await agent.run("你好")


async def test_none_content_without_tool_calls_is_rejected() -> None:
    response = llm_models.LLMResponse(content=None, finish_reason="stop", usage=_usage())
    agent = Agent(StubLLM(response))

    with pytest.raises(LLMEmptyResponseError):
        await agent.run("你好")


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
async def test_blank_content_is_rejected(content: str) -> None:
    response = llm_models.LLMResponse(content=content, finish_reason="stop", usage=_usage())
    agent = Agent(StubLLM(response))

    with pytest.raises(LLMEmptyResponseError):
        await agent.run("你好")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reply": "", "steps": 1},
        {"reply": "   ", "steps": 1},
        {"reply": "答案", "steps": 0},
        {"reply": "答案", "steps": -1},
    ],
)
def test_agent_result_rejects_invalid_fields(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate({**kwargs, "usage": _usage()})


def test_agent_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate({"reply": "答案", "steps": 1, "usage": _usage(), "unknown": []})


def _response(content: str) -> llm_models.LLMResponse:
    return llm_models.LLMResponse(content=content, finish_reason="stop", usage=_usage())
