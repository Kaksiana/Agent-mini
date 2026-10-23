"""S16 TC-L1-014/023/026/027、TC-L3-014：整轮裁剪。"""

from __future__ import annotations

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
    result = _fit([_round(index, width=40) for index in range(12)], 600)

    assert result.trim_reason == "tokens"
    assert result.tokens_after <= 600
    assert result.tokens_before > 600
    assert result.rounds_after < 12


def test_both_trigger_reason_is_accurate() -> None:
    result = _fit([_round(index, width=80) for index in range(12)], 600)

    assert result.trim_reason in {"both", "tokens"}
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
