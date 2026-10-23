"""TC-L3-001/002/005/014：Redis 短时窗口。"""

import asyncio
import logging
from pathlib import Path
from typing import Any, cast

import fakeredis.aioredis
import pytest

from agent_mini.llm import models as llm_models
from agent_mini.llm.client import LLMClient
from agent_mini.memory.base import StoredRound
from agent_mini.memory.short_term import ShortTermMemory
from agent_mini.runtime.agent import Agent

pytestmark = pytest.mark.integration


def _user(text: str) -> llm_models.Message:
    return llm_models.Message(role="user", content=text)


def _tool_round() -> list[llm_models.Message]:
    call = llm_models.ToolCall(id="call_1", name="echo", arguments={"text": "x"})
    return [
        _user("hi"),
        llm_models.Message(role="assistant", content=None, tool_calls=[call]),
        llm_models.Message(role="tool", content="ok", tool_call_id="call_1"),
        llm_models.Message(role="assistant", content="done", reasoning_content="private"),
    ]


@pytest.fixture
async def client() -> Any:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


async def test_rounds_are_complete_and_ltrimmed(client: Any) -> None:
    memory = ShortTermMemory(client, max_rounds=2)
    for round_id in ("r1", "r2", "r3"):
        assert await memory.append_round("A", [_user(round_id)], round_id) is True

    rounds = await memory.get_recent_rounds("A", 2)

    assert [round_.messages[0].content for round_ in rounds] == ["r2", "r3"]


async def test_tool_pair_and_reasoning_are_preserved(client: Any) -> None:
    memory = ShortTermMemory(client)
    messages = _tool_round()

    await memory.append_round("A", messages, "r1")
    restored = (await memory.get_recent_rounds("A"))[0]

    assert restored.messages[1].tool_calls is not None
    assert restored.messages[1].tool_calls[0].id == "call_1"
    assert restored.messages[2].tool_call_id == "call_1"
    assert restored.messages[3].reasoning_content == "private"


async def test_ttl_expires_window(client: Any) -> None:
    memory = ShortTermMemory(client, ttl_seconds=1)
    await memory.append_round("A", [_user("x")], "r1")

    await asyncio.sleep(1.1)
    rounds = await memory.get_recent_rounds("A")

    assert rounds == []


async def test_sessions_are_isolated(client: Any) -> None:
    memory = ShortTermMemory(client)
    await memory.append_round("A", [_user("a")], "r1")
    await memory.append_round("B", [_user("b")], "r1")

    a_rounds = await memory.get_recent_rounds("A")
    b_rounds = await memory.get_recent_rounds("B")

    assert a_rounds[0].messages[0].content == "a"
    assert b_rounds[0].messages[0].content == "b"


class _BrokenClient:
    async def rpush(self, *args: object) -> None:
        raise ConnectionError("down")

    async def ltrim(self, *args: object) -> None:
        raise ConnectionError("down")

    async def expire(self, *args: object) -> None:
        raise ConnectionError("down")

    async def lrange(self, *args: object) -> list[str]:
        raise ConnectionError("down")

    async def eval(self, *args: object) -> None:
        raise ConnectionError("down")


@pytest.mark.parametrize(("max_rounds", "ttl"), [(0, 1), (1, 0), (True, 1), (1, True)])
def test_invalid_constructor_arguments(
    client: Any,
    max_rounds: int,
    ttl: int,
) -> None:
    with pytest.raises(ValueError):
        ShortTermMemory(client, max_rounds=max_rounds, ttl_seconds=ttl)


async def test_corrupt_round_is_skipped(client: Any) -> None:
    memory = ShortTermMemory(client)
    await memory.append_round("A", [_user("good")], "r1")
    await client.rpush(memory.key("A"), "not-json")

    rounds = await memory.get_recent_rounds("A")

    assert [round_.messages[0].content for round_ in rounds] == ["good"]


def test_bind_request_preserves_sandbox_fields(tmp_path: Path) -> None:
    from agent_mini.runtime.registry_adapter import RegistryExecutor
    from agent_mini.tools.registry import ToolContext, ToolRegistry

    executor = RegistryExecutor(
        ToolRegistry(),
        ToolContext("old", "old-trace", sandbox_root=str(tmp_path), max_file_size=1024),
    )
    bound = executor.bind_request("new", "new-trace")

    assert bound._context is not None
    assert bound._context.session_id == "new"
    assert bound._context.sandbox_root == str(tmp_path)
    assert bound._context.max_file_size == 1024


async def test_redis_failure_degrades_without_raise(
    caplog: pytest.LogCaptureFixture,
) -> None:
    memory = ShortTermMemory(cast(Any, _BrokenClient()))

    with caplog.at_level(logging.WARNING):
        written = await memory.append_round("A", [_user("x")], "r1")
        rounds = await memory.get_recent_rounds("A")

    assert written is False
    assert rounds == []
    assert "memory.degraded" in caplog.text


class _OrderedStore:
    def __init__(self) -> None:
        self.written = False
        self.messages: list[llm_models.Message] = []

    async def append_round(
        self,
        session_id: str,
        messages: list[llm_models.Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        self.written = True
        self.messages = messages
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return []


class _StubLLM:
    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        return llm_models.LLMResponse(
            content="ok",
            finish_reason="stop",
            usage=llm_models.Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_agent_degrades_when_memory_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    memory = ShortTermMemory(cast(Any, _BrokenClient()))
    agent = Agent(cast(LLMClient, _StubLLM()), short_term=memory)

    with caplog.at_level(logging.WARNING):
        result = await agent.run("hi", session_id="A")

    assert result.reply == "ok"
    assert "memory.degraded" in caplog.text


class _HangingStore:
    async def append_round(
        self,
        session_id: str,
        messages: list[llm_models.Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        await asyncio.sleep(10)
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return []


async def test_agent_timeout_degrades(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import agent_mini.runtime.agent as agent_module

    monkeypatch.setattr(agent_module, "MEMORY_WRITEBACK_TIMEOUT_SECONDS", 0.01)
    agent = Agent(cast(LLMClient, _StubLLM()), short_term=_HangingStore(), memory_timeout=0.01)

    with caplog.at_level(logging.WARNING):
        result = await agent.run("hi", session_id="A")

    assert result.reply == "ok"
    assert "memory.degraded" in caplog.text


async def test_agent_writes_back_before_return() -> None:
    store = _OrderedStore()
    agent = Agent(cast(LLMClient, _StubLLM()), short_term=store)

    result = await agent.run("hi", session_id="A")

    assert store.written is True
    assert result.session_id == "A"
    assert store.messages[0].content == "hi"
    assert store.messages[-1].content == "ok"
