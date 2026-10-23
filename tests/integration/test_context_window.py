"""S16 TC-L1-014/023/026/027、TC-L3-014：整轮裁剪。"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from agent_mini.context.builder import BuildRequest, ContextBuilder
from agent_mini.context.token_counter import TokenCounter
from agent_mini.context.window import ContextTooLarge, FitInput, fit_rounds
from agent_mini.llm.models import LLMResponse, Message, ToolCall, ToolSchema, Usage
from agent_mini.memory.base import StoredRound
from agent_mini.runtime.agent import Agent
from agent_mini.tools.registry import ToolResult

pytestmark = pytest.mark.integration


class Encoder:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))


def _round(index: int, width: int = 1) -> StoredRound:
    call = ToolCall(id=f"call_{index}", name="echo", arguments={})
    return StoredRound(
        f"r{index}",
        (
            Message(role="user", content="u" * width),
            Message(role="assistant", content=None, tool_calls=[call]),
            Message(role="tool", content="t" * width, tool_call_id=f"call_{index}"),
            Message(role="assistant", content="a" * width, reasoning_content="p"),
        ),
    )


def _fit(history: list[StoredRound], budget: int) -> Any:
    return fit_rounds(
        history,
        FitInput(
            prefix=[Message(role="system", content="system")],
            current=[Message(role="user", content="current")],
            tools_snapshot=[],
            counter=TokenCounter(Encoder()),
            budget=budget,
            include_reasoning=True,
        ),
    )


def test_rounds_trigger_keeps_last_k_whole_rounds() -> None:
    result = _fit([_round(index) for index in range(12)], 1_000_000)

    assert result.rounds_before == 12
    assert result.rounds_after == 10
    assert result.dropped_rounds == 2
    assert result.trim_reason == "rounds"
    assert result.messages[0].content == "system"
    assert result.messages[-1].content == "current"
    assert len(result.messages) == 1 + 10 * 4 + 1


def test_tokens_trigger_recounts_after_each_drop() -> None:
    result = _fit([_round(index, width=200) for index in range(8)], 600)

    assert result.trim_reason == "tokens"
    assert result.tokens_after <= 600
    assert result.tokens_before > 600
    assert result.rounds_after < 12


def test_both_trigger_reason_is_accurate() -> None:
    result = _fit([_round(index, width=80) for index in range(12)], 600)

    assert result.trim_reason == "both"
    assert result.tokens_after <= 600


def test_system_and_current_are_never_dropped() -> None:
    result = _fit([_round(index, width=80) for index in range(12)], 600)

    assert result.messages[0].content == "system"
    assert result.messages[-1].content == "current"


def test_minimal_set_over_budget_raises() -> None:
    with pytest.raises(ContextTooLarge):
        _fit([], 1)


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            content="ok",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


class _Executor:
    def schemas(self) -> list[ToolSchema]:
        return []

    async def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(True, "ok", None)


async def test_too_large_does_not_call_llm() -> None:
    llm = _LLM()
    builder = ContextBuilder(TokenCounter(Encoder()), max_context_tokens=100)
    agent = Agent(cast(Any, llm), tool_executor=_Executor()).with_context(builder)

    with pytest.raises(ContextTooLarge):
        await agent.run("current", session_id="A")

    assert llm.calls == 0


class _MemoryShort:
    def __init__(self) -> None:
        self.rounds: list[StoredRound] = []

    async def append_round(
        self,
        session_id: str,
        messages: list[Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        self.rounds.append(StoredRound(round_id, tuple(messages), truncated, termination_reason))
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return list(self.rounds)


async def test_three_turns_store_only_current_round() -> None:
    store = _MemoryShort()
    builder = ContextBuilder(TokenCounter(Encoder()), max_context_tokens=1_000_000)
    agent = Agent(cast(Any, _LLM()), short_term=store).with_context(builder)

    await agent.run("first", session_id="A")
    await agent.run("second", session_id="A")
    await agent.run("third", session_id="A")

    assert len(store.rounds) == 3
    for stored in store.rounds:
        assert stored.messages[0].role == "user"
        assert stored.messages[0].content in {"first", "second", "third"}
        assert all(message.role != "system" for message in stored.messages)


async def test_fit_is_bounded_by_deadline() -> None:
    from agent_mini.runtime.loop import LoopPolicy

    class HangingShort:
        def __init__(self) -> None:
            self.calls = 0

        async def append_round(self, *args: object, **kwargs: object) -> bool:
            return True

        async def get_recent_rounds(
            self,
            session_id: str,
            limit: int | None = None,
        ) -> list[StoredRound]:
            self.calls += 1
            if self.calls > 1:
                await asyncio.sleep(1)
            return []

    llm = _LLM()
    builder = ContextBuilder(
        TokenCounter(Encoder()),
        max_context_tokens=100_000,
        read_timeout_seconds=0.5,
    )
    agent = Agent(
        cast(Any, llm),
        policy=LoopPolicy(deadline_seconds=0.01),
        short_term=cast(Any, HangingShort()),
    ).with_context(builder)

    result = await agent.run("current", session_id="A")

    assert result.truncated is True
    assert result.termination_reason == "deadline"
    assert llm.calls == 0


class _ToolLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                tool_calls=[ToolCall(id="call_big", name="echo", arguments={})],
                finish_reason="tool_calls",
                usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        return LLMResponse(content="unexpected", finish_reason="stop", usage=Usage())


class _HugeExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def schemas(self) -> list[ToolSchema]:
        return [
            ToolSchema(
                name="echo",
                description="echo",
                parameters={"type": "object"},
            )
        ]

    async def execute(self, call: ToolCall) -> ToolResult:
        self.calls += 1
        return ToolResult(True, "x" * 6000, None)


async def test_tool_overflow_keeps_trace_and_does_not_replay() -> None:
    llm = _ToolLLM()
    executor = _HugeExecutor()
    builder = ContextBuilder(
        TokenCounter(Encoder()),
        max_context_tokens=2_000,
        max_output_tokens=1_024,
    )
    agent = Agent(cast(Any, llm), tool_executor=executor).with_context(builder)

    with pytest.raises(ContextTooLarge) as error:
        await agent.run("current", session_id="A")

    assert llm.calls == 1
    assert executor.calls == 1
    assert error.value.steps >= 2
    assert len(error.value.trace) >= 1
    assert len(error.value.tool_traces) == 1


async def test_builder_payload_tracks_trim_fields() -> None:
    class Short:
        async def append_round(self, *args: object, **kwargs: object) -> bool:
            return True

        async def get_recent_rounds(
            self,
            session_id: str,
            limit: int | None = None,
        ) -> list[StoredRound]:
            return [_round(index) for index in range(12)]

    builder = ContextBuilder(TokenCounter(Encoder()), max_context_tokens=1_000_000)
    payload = await builder.build(
        BuildRequest(
            "current",
            [],
            session_id="A",
            short_term=cast(Any, Short()),
        )
    )

    assert payload.rounds_before == 12
    assert payload.rounds_after == 10
    assert payload.trim_reason == "rounds"
    assert payload.tokens_before >= payload.tokens_after
