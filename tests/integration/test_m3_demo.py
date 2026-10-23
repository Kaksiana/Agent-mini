"""M3 离线演示：三轮记忆、跨轮上下文与整轮裁剪。"""

from __future__ import annotations

from typing import Any, cast

import pytest

from agent_mini.context.builder import ContextBuilder
from agent_mini.context.token_counter import TokenCounter
from agent_mini.context.window import FitInput, fit_rounds
from agent_mini.llm.models import LLMResponse, Message, ToolSchema, Usage
from agent_mini.memory.base import StoredRound
from agent_mini.runtime.agent import Agent

pytestmark = pytest.mark.integration


class Encoder:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))


class Short:
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


class LLM:
    def __init__(self) -> None:
        self.requests: list[list[Message]] = []

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.requests.append(list(messages))
        return LLMResponse(
            content="answer",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_m3_cross_turn_memory_and_trim_demo() -> None:
    short = Short()
    llm = LLM()
    builder = ContextBuilder(TokenCounter(Encoder()), max_context_tokens=1_000_000)
    agent = Agent(cast(Any, llm), short_term=short).with_context(builder)

    await agent.run("first", session_id="A")
    await agent.run("second", session_id="A")
    await agent.run("third", session_id="A")

    assert [round_.messages[0].content for round_ in short.rounds] == [
        "first",
        "second",
        "third",
    ]
    assert llm.requests[-1][0].content == "first"
    assert llm.requests[-1][-1].content == "third"

    history = [
        StoredRound(
            f"demo-{index}",
            (
                Message(role="user", content=f"turn-{index}"),
                Message(role="assistant", content="ok"),
            ),
        )
        for index in range(12)
    ]
    result = fit_rounds(
        history,
        FitInput(
            prefix=[Message(role="system", content="system")],
            current=[Message(role="user", content="current")],
            tools_snapshot=[],
            counter=TokenCounter(Encoder()),
            budget=1_000_000,
            include_reasoning=True,
        ),
    )

    assert result.rounds_before == 12
    assert result.rounds_after == 10
    assert result.trim_reason == "rounds"
    assert result.messages[0].content == "system"
    assert result.messages[-1].content == "current"
