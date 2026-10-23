"""TC-L3-003/004/014：MongoDB 中期存储与检索。"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import mongomock
import pytest
from mongomock.collection import Collection

from agent_mini.llm import models as llm_models
from agent_mini.llm.client import LLMClient
from agent_mini.memory.base import StoredRound
from agent_mini.memory.mid_term import INDEX_NAME, MidTermMemory
from agent_mini.runtime.agent import Agent

pytestmark = pytest.mark.integration


class _AsyncCursor:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def sort(self, key: str, direction: int) -> _AsyncCursor:
        self._cursor = self._cursor.sort(key, direction)
        return self

    def limit(self, count: int) -> _AsyncCursor:
        self._cursor = self._cursor.limit(count)
        return self

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        return list(self._cursor[:length])


class AsyncMongomock:
    def __init__(self, collection: Any) -> None:
        self._collection = collection
        self.raw = collection

    async def index_information(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._collection.index_information())

    async def create_index(self, keys: list[tuple[str, int]], name: str) -> str:
        return cast(str, self._collection.create_index(keys, name=name))

    async def insert_one(self, document: dict[str, Any]) -> Any:
        return self._collection.insert_one(document)

    def find(self, query: dict[str, Any]) -> _AsyncCursor:
        return _AsyncCursor(self._collection.find(query))


def _round(text: str, reasoning: str | None = None) -> StoredRound:
    messages = [
        llm_models.Message(role="user", content=text),
        llm_models.Message(role="assistant", content="ok", reasoning_content=reasoning),
    ]
    return StoredRound("r1", tuple(messages), False, None)


@pytest.fixture
def memory() -> MidTermMemory:
    collection = cast(Collection, mongomock.MongoClient()["db"]["rounds"])
    return MidTermMemory(AsyncMongomock(collection))


async def test_write_and_query_session(memory: MidTermMemory) -> None:
    await memory.ensure_indexes()
    assert await memory.append_round("A", _round("alpha"), datetime.now(UTC)) is True

    rows = await memory.search_rounds("A")

    assert len(rows) == 1
    assert rows[0].round_id == "r1"
    assert rows[0].messages[0].content == "alpha"


async def test_keyword_and_time_order(memory: MidTermMemory) -> None:
    now = datetime.now(UTC)
    await memory.append_round("A", _round("old weather"), now - timedelta(hours=2))
    await memory.append_round("A", _round("new weather"), now)
    await memory.append_round("B", _round("weather B"), now)

    rows = await memory.search_rounds("A", keyword="weather")

    assert [row.messages[0].content for row in rows] == ["new weather", "old weather"]


async def test_cross_session_isolation(memory: MidTermMemory) -> None:
    await memory.append_round("A", _round("alpha"))
    await memory.append_round("B", _round("beta"))

    a_rows = await memory.search_rounds("A")
    b_rows = await memory.search_rounds("B")

    assert [row.messages[0].content for row in a_rows] == ["alpha"]
    assert [row.messages[0].content for row in b_rows] == ["beta"]


async def test_reasoning_not_in_public_results(memory: MidTermMemory) -> None:
    await memory.append_round("A", _round("alpha", reasoning="private"))

    public = (await memory.search_rounds("A"))[0]
    private = (await memory.search_rounds("A", include_private=True))[0]

    assert public.messages[1].reasoning_content is None
    assert private.messages[1].reasoning_content == "private"


def test_from_uri_builds_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    import agent_mini.memory.mid_term as module

    class FakeClient:
        def __getitem__(self, name: str) -> FakeClient:
            return self

    monkeypatch.setattr(module, "AsyncMongoClient", lambda *args, **kwargs: FakeClient())
    memory = MidTermMemory.from_uri("mongodb://example")

    assert isinstance(memory, MidTermMemory)


async def test_index_is_idempotent(memory: MidTermMemory) -> None:
    assert await memory.ensure_indexes() is True
    assert await memory.ensure_indexes() is True

    collection = cast(AsyncMongomock, memory._collection).raw
    indexes = collection.index_information()
    assert INDEX_NAME in indexes


class _BrokenCollection:
    async def index_information(self) -> dict[str, Any]:
        raise ConnectionError("down")

    async def create_index(self, keys: list[tuple[str, int]], name: str) -> str:
        raise ConnectionError("down")

    async def insert_one(self, document: dict[str, Any]) -> None:
        raise ConnectionError("down")

    def find(self, query: dict[str, Any]) -> _AsyncCursor:
        raise ConnectionError("down")


async def test_mongo_failure_degrades(caplog: pytest.LogCaptureFixture) -> None:
    memory = MidTermMemory(_BrokenCollection())

    with caplog.at_level(logging.WARNING):
        assert await memory.ensure_indexes() is False
        assert await memory.append_round("A", _round("x")) is False
        assert await memory.search_rounds("A") == []

    assert "memory.degraded" in caplog.text


class _SlowMidTerm:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = False

    async def append_round(self, session_id: str, stored: StoredRound) -> bool:
        self.started.set()
        await self.release.wait()
        self.finished = True
        return True

    async def drain(self) -> None:
        return


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


class _FailingMidTerm:
    async def append_round(self, session_id: str, stored: StoredRound) -> bool:
        raise ConnectionError("down")

    async def drain(self) -> None:
        return


class _CapturedMid:
    def __init__(self) -> None:
        self.stored: StoredRound | None = None

    async def append_round(self, session_id: str, stored: StoredRound) -> bool:
        self.stored = stored
        return True

    async def drain(self) -> None:
        return


class _ShortCapture:
    def __init__(self) -> None:
        self.round_id: str | None = None

    async def append_round(
        self,
        session_id: str,
        messages: list[llm_models.Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        self.round_id = round_id
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return []


async def test_round_id_is_shared_across_stores() -> None:
    short = _ShortCapture()
    mid = _CapturedMid()
    agent = Agent(cast(LLMClient, _StubLLM()), short_term=short).with_mid_term(mid, 1.0)

    await agent.run("hi", session_id="A")
    await agent.drain()

    assert mid.stored is not None
    assert short.round_id == mid.stored.round_id


async def test_full_tool_round_raw_document(memory: MidTermMemory) -> None:
    call = llm_models.ToolCall(id="call_1", name="echo", arguments={"x": 1})
    messages = (
        llm_models.Message(role="user", content="hello"),
        llm_models.Message(role="assistant", content=None, tool_calls=[call]),
        llm_models.Message(role="tool", content="ok", tool_call_id="call_1"),
        llm_models.Message(role="assistant", content="done", reasoning_content="private"),
    )
    await memory.append_round("A", StoredRound("r1", messages, False, None))

    document = cast(AsyncMongomock, memory._collection).raw.find_one({"session_id": "A"})

    assert document is not None
    assert document["round_id"] == "r1"
    assert document["messages"][1]["tool_calls"][0]["id"] == "call_1"
    assert document["messages"][2]["tool_call_id"] == "call_1"
    assert document["messages"][3]["reasoning_content"] == "private"


async def test_index_same_name_different_key_is_rejected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    collection = cast(Collection, mongomock.MongoClient()["db"]["rounds"])
    cast(Any, collection).create_index([("session_id", 1)], name=INDEX_NAME)
    memory = MidTermMemory(AsyncMongomock(collection))

    with caplog.at_level(logging.WARNING):
        assert await memory.ensure_indexes() is False

    assert "memory.index_conflict" in caplog.text


async def test_invalid_session_is_rejected(memory: MidTermMemory) -> None:
    assert await memory.append_round(" ", _round("x")) is False
    assert await memory.search_rounds("") == []


async def test_agent_rejects_invalid_session() -> None:
    agent = Agent(cast(LLMClient, _StubLLM()))

    with pytest.raises(ValueError):
        await agent.run("hi", session_id="")


class _TimedOutMid:
    async def append_round(self, session_id: str, stored: StoredRound) -> bool:
        await asyncio.sleep(0.05)
        return True

    async def drain(self) -> None:
        return


async def test_agent_mongo_timeout_degrades(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = Agent(cast(LLMClient, _StubLLM())).with_mid_term(_TimedOutMid(), 0.001)

    with caplog.at_level(logging.WARNING):
        result = await agent.run("hi", session_id="A")
        await agent.drain()

    assert result.reply == "ok"
    assert "memory.degraded" in caplog.text


async def test_agent_mongo_failure_does_not_block(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = Agent(cast(LLMClient, _StubLLM())).with_mid_term(
        cast(Any, _FailingMidTerm()),
        0.1,
    )

    with caplog.at_level(logging.WARNING):
        result = await agent.run("hi", session_id="A")
        await agent.drain()

    assert result.reply == "ok"
    assert "memory.degraded" in caplog.text


async def test_agent_mongo_write_is_async() -> None:
    mid = _SlowMidTerm()
    agent = Agent(
        cast(LLMClient, _StubLLM()),
    ).with_mid_term(cast(Any, mid), 1.0)

    result = await agent.run("hi", session_id="A")
    await mid.started.wait()

    assert result.reply == "ok"
    assert mid.finished is False
    mid.release.set()
    await asyncio.sleep(0.01)
    assert mid.finished is True
