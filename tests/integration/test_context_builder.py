"""TC-L1-013/022/025、TC-L3-007：Context 拼接与计数。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import pytest

from agent_mini.context.builder import BuildRequest, ContextBuilder
from agent_mini.context.token_counter import (
    DEFAULT_PROTOCOL_OVERHEAD_TOKENS,
    TokenCounter,
    canonical_json,
)
from agent_mini.llm.models import LLMResponse, Message, ToolCall, ToolSchema, Usage
from agent_mini.memory.base import StoredRound
from agent_mini.tools.registry import ToolResult

pytestmark = pytest.mark.integration


class FakeEncoder:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))


class RecordingCounter:
    def __init__(self) -> None:
        self.received: tuple[ToolSchema, ...] | None = None

    def count_request(
        self,
        messages: list[Message],
        tools: tuple[ToolSchema, ...],
        include_reasoning: bool = True,
    ) -> Any:
        self.received = tools
        return TokenCounter(FakeEncoder()).count_request(
            messages,
            tools,
            include_reasoning,
        )


class FakeShort:
    def __init__(self, rounds: list[StoredRound]) -> None:
        self.rounds = rounds

    async def append_round(self, *args: object, **kwargs: object) -> bool:
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return self.rounds


class FakeMid:
    def __init__(self, rounds: list[StoredRound]) -> None:
        self.rounds = rounds

    async def append_round(self, *args: object, **kwargs: object) -> bool:
        return True

    async def drain(self) -> None:
        return

    async def get_rounds(self, session_id: str, limit: int = 100) -> list[StoredRound]:
        return self.rounds


def _round(round_id: str, text: str) -> StoredRound:
    return StoredRound(
        round_id,
        (
            Message(role="user", content=text),
            Message(role="assistant", content="ok", reasoning_content="private"),
        ),
    )


def _tools(description: str = "echo") -> list[ToolSchema]:
    return [
        ToolSchema(
            name="echo",
            description=description,
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
    ]


async def test_five_rounds_order_and_system_first() -> None:
    rounds = [_round(f"r{index}", f"history-{index}") for index in range(5)]
    builder = ContextBuilder(TokenCounter(FakeEncoder()), 16_000)

    payload = await builder.build(
        BuildRequest(
            "current",
            _tools(),
            session_id="A",
            short_term=cast(Any, FakeShort(rounds)),
            system_prompt="system",
        )
    )

    assert payload.messages[0] == Message(role="system", content="system")
    assert payload.messages[-1] == Message(role="user", content="current")
    assert payload.trim_reason is None
    assert [message.content for message in payload.messages[1:-1]] == [
        "history-0",
        "ok",
        "history-1",
        "ok",
        "history-2",
        "ok",
        "history-3",
        "ok",
        "history-4",
        "ok",
    ]


async def test_tools_snapshot_identity_and_budget() -> None:
    counter = RecordingCounter()
    tools = _tools()
    builder = ContextBuilder(cast(Any, counter), 16_000, 1024)

    payload = await builder.build(BuildRequest("hi", tools))

    assert isinstance(payload.tools_snapshot, tuple)
    assert payload.tools_snapshot == tuple(tools)
    assert counter.received is payload.tools_snapshot
    assert payload.budget == 13_376
    assert payload.estimated_input_tokens == (
        payload.message_tokens + payload.tool_schema_tokens + payload.protocol_overhead_tokens
    )
    assert payload.protocol_overhead_tokens == DEFAULT_PROTOCOL_OVERHEAD_TOKENS


def test_schema_changes_count() -> None:
    counter = TokenCounter(FakeEncoder())
    messages = [Message(role="user", content="hi")]

    short = counter.count_request(messages, _tools())
    long = counter.count_request(messages, _tools("long description " * 10))

    assert short.tool_schema_tokens > 0
    assert long.tool_schema_tokens > short.tool_schema_tokens


def test_count_is_reproducible_and_sorted() -> None:
    first = {
        "type": "object",
        "properties": {"b": {"type": "string"}, "a": {"type": "integer"}},
    }
    second = {
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
        "type": "object",
    }
    assert canonical_json(first) == canonical_json(second)
    counter = TokenCounter(FakeEncoder())
    messages = [Message(role="user", content="hi")]
    assert counter.count_request(messages, _tools()).estimated_input_tokens == (
        counter.count_request(messages, _tools()).estimated_input_tokens
    )


def test_reasoning_serialization_toggle() -> None:
    counter = TokenCounter(FakeEncoder())
    messages = [
        Message(
            role="assistant",
            content="ok",
            reasoning_content="very long private reasoning " * 20,
        )
    ]

    with_reasoning = counter.count_request(messages, [])
    without_reasoning = counter.count_request(messages, [], include_reasoning=False)

    assert with_reasoning.message_tokens > without_reasoning.message_tokens


def test_empty_messages_and_tools_are_zero() -> None:
    counts = TokenCounter(FakeEncoder()).count_request([], [])

    assert counts.estimated_input_tokens == 0
    assert counts.protocol_overhead_tokens == 0


def test_degraded_counter_still_counts_schema(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import agent_mini.context.token_counter as module

    def broken(name: str) -> object:
        raise RuntimeError("no encoding")

    monkeypatch.setattr(module, "_load_encoder", broken)
    counter = TokenCounter()

    with caplog.at_level(logging.WARNING):
        counts = counter.count_request(
            [Message(role="user", content="hello")],
            _tools(),
        )

    assert counts.tool_schema_tokens > 0
    assert counts.estimated_input_tokens > 0
    assert "token_counter.degraded" in caplog.text


class HangingShort:
    async def append_round(self, *args: object, **kwargs: object) -> bool:
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        await asyncio.sleep(10)
        return []


async def test_memory_read_timeout_degrades() -> None:
    builder = ContextBuilder(
        TokenCounter(FakeEncoder()),
        16_000,
        read_timeout_seconds=0.01,
    )

    payload = await builder.build(
        BuildRequest("current", [], session_id="A", short_term=cast(Any, HangingShort()))
    )

    assert [message.content for message in payload.messages] == ["current"]


async def test_duplicate_round_ids_are_removed() -> None:
    duplicate = _round("same", "once")
    mid = FakeMid([duplicate, duplicate])
    short = FakeShort([duplicate])
    builder = ContextBuilder(TokenCounter(FakeEncoder()), 16_000)

    payload = await builder.build(
        BuildRequest(
            "current",
            [],
            session_id="A",
            mid_term=cast(Any, mid),
            short_term=cast(Any, short),
        )
    )

    assert [message.content for message in payload.messages] == ["once", "ok", "current"]


class FakeExecutor:
    def __init__(self, tools: list[ToolSchema]) -> None:
        self.core = tools

    def schemas(self) -> list[ToolSchema]:
        return self.core

    async def execute(self, call: ToolCall) -> ToolResult:
        return ToolResult(True, "ok", None)


async def test_agent_uses_builder_snapshot_for_llm() -> None:
    from agent_mini.runtime.agent import Agent

    class AgentLLM:
        def __init__(self) -> None:
            self.tools: Any = None
            self.messages: list[Message] | None = None

        async def chat(
            self,
            messages: list[Message],
            tools: Any = None,
            **params: object,
        ) -> LLMResponse:
            self.tools = tools
            self.messages = list(messages)
            return LLMResponse(
                content="ok",
                finish_reason="stop",
                usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

    llm = AgentLLM()
    tools = _tools()
    builder = ContextBuilder(TokenCounter(FakeEncoder()), 16_000)
    agent = Agent(cast(Any, llm), tool_executor=FakeExecutor(tools)).with_context(
        builder,
        system_prompt="system",
    )

    await agent.run("current", session_id="A")

    assert isinstance(llm.tools, list)
    assert llm.tools == tools
    assert llm.messages is not None
    assert llm.messages[0].content == "system"
    assert llm.messages[-1].content == "current"


async def test_mid_term_rounds_are_consumed() -> None:
    mid = FakeMid([_round("m1", "from-mongo")])
    builder = ContextBuilder(TokenCounter(FakeEncoder()), 16_000)

    payload = await builder.build(
        BuildRequest(
            "current",
            [],
            session_id="A",
            mid_term=cast(Any, mid),
        )
    )

    assert [message.content for message in payload.messages] == [
        "from-mongo",
        "ok",
        "current",
    ]


async def test_cross_store_merge_keeps_short_order() -> None:
    mid = [_round("r1", "one"), _round("r3", "three")]
    short = [_round("r1", "one"), _round("r2", "two"), _round("r3", "three")]
    builder = ContextBuilder(TokenCounter(FakeEncoder()), 16_000)
    payload = await builder.build(
        BuildRequest(
            "current",
            _tools(),
            session_id="A",
            short_term=cast(Any, FakeShort(short)),
            mid_term=cast(Any, FakeMid(mid)),
        )
    )
    contents = [message.content for message in payload.messages]
    assert contents.index("one") < contents.index("two") < contents.index("three")
