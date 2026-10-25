"""真实 Redis/Mongo 记忆往返（Docker gated）。"""

from __future__ import annotations

import os
from typing import Any, cast
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from agent_mini.context.builder import BuildRequest, ContextBuilder
from agent_mini.context.token_counter import TokenCounter
from agent_mini.llm.models import Message
from agent_mini.memory.base import StoredRound
from agent_mini.memory.mid_term import COLLECTION_NAME, MidTermMemory
from agent_mini.memory.short_term import ShortTermMemory

pytestmark = pytest.mark.integration
REDIS_URL = "REDIS_TEST_URL"
MONGO_URI = "MONGO_TEST_URI"


@pytest.mark.skipif(not os.environ.get(REDIS_URL), reason="REDIS_TEST_URL 未配置")
async def test_redis_real_round_trip() -> None:
    client = Redis.from_url(os.environ[REDIS_URL])
    memory = ShortTermMemory(client, max_rounds=3)
    session = f"real-{uuid4().hex}"
    messages = [Message(role="user", content="hello"), Message(role="assistant", content="ok")]
    assert await memory.append_round(session, messages, "r1") is True
    rounds = await memory.get_recent_rounds(session)
    assert len(rounds) == 1
    assert rounds[0].messages[0].content == "hello"
    await client.delete(memory.key(session))
    await client.aclose()


@pytest.mark.skipif(not os.environ.get(MONGO_URI), reason="MONGO_TEST_URI 未配置")
async def test_mongo_real_round_trip() -> None:
    client: AsyncMongoClient[dict[str, object]] = AsyncMongoClient(os.environ[MONGO_URI])
    database = client[f"agent_mini_test_{uuid4().hex}"]
    memory = MidTermMemory(cast(Any, database[COLLECTION_NAME]))
    assert await memory.ensure_indexes() is True
    session = f"real-{uuid4().hex}"
    round_ = StoredRound(
        "r1",
        (Message(role="user", content="mongo-hello"), Message(role="assistant", content="ok")),
    )
    assert await memory.append_round(session, round_) is True
    rounds = await memory.search_rounds(session)
    assert len(rounds) == 1
    assert rounds[0].messages[0].content == "mongo-hello"
    await database.drop_collection(COLLECTION_NAME)
    await client.close()


@pytest.mark.skipif(
    not (os.environ.get(REDIS_URL) and os.environ.get(MONGO_URI)),
    reason="REDIS_TEST_URL/MONGO_TEST_URI 未配置",
)
async def test_real_redis_mongo_context_chain() -> None:
    redis_client = Redis.from_url(os.environ[REDIS_URL])
    mongo_client: AsyncMongoClient[dict[str, object]] = AsyncMongoClient(os.environ[MONGO_URI])
    database = mongo_client[f"agent_mini_ctx_{uuid4().hex}"]
    short = ShortTermMemory(redis_client, max_rounds=5)
    mid = MidTermMemory(cast(Any, database[COLLECTION_NAME]))
    session = f"real-{uuid4().hex}"
    r1 = StoredRound(
        "r1", (Message(role="user", content="one"), Message(role="assistant", content="ok"))
    )
    r2 = StoredRound(
        "r2", (Message(role="user", content="two"), Message(role="assistant", content="ok"))
    )
    r3 = StoredRound(
        "r3", (Message(role="user", content="three"), Message(role="assistant", content="ok"))
    )
    assert await short.append_round(session, list(r1.messages), "r1")
    assert await short.append_round(session, list(r2.messages), "r2")
    assert await short.append_round(session, list(r3.messages), "r3")
    assert await mid.append_round(session, r1)
    assert await mid.append_round(session, r3)
    builder = ContextBuilder(TokenCounter(), 16_000)
    payload = await builder.build(
        BuildRequest("current", [], session_id=session, short_term=short, mid_term=mid)
    )
    contents = [message.content for message in payload.messages]
    assert contents.index("one") < contents.index("two") < contents.index("three")
    await redis_client.delete(short.key(session))
    await database.drop_collection(COLLECTION_NAME)
    await short.close()
    await mid.close()
    await mongo_client.close()
