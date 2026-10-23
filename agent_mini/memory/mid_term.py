"""S14 MongoDB 中期存储与检索。"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Protocol, cast

from pymongo import AsyncMongoClient

from agent_mini.llm.models import Message
from agent_mini.memory.base import StoredRound

COLLECTION_NAME = "conversation_rounds"
DATABASE_NAME = "agent_mini"
INDEX_NAME = "session_created_desc"
DEFAULT_SEARCH_LIMIT = 20
SERVER_SELECTION_TIMEOUT_MS = 2_000
LOGGER = logging.getLogger("agent_mini.memory")


class _AsyncCursor(Protocol):
    def sort(self, key: str, direction: int) -> _AsyncCursor: ...
    def limit(self, count: int) -> _AsyncCursor: ...
    async def to_list(self, length: int) -> list[dict[str, object]]: ...


class _AsyncCollection(Protocol):
    async def index_information(self) -> dict[str, object]: ...
    async def create_index(
        self,
        keys: list[tuple[str, int]],
        name: str,
    ) -> object: ...
    async def insert_one(self, document: dict[str, object]) -> object: ...
    def find(self, query: dict[str, object]) -> _AsyncCursor: ...


class MidTermMemory:
    """按 session 存储完整轮次，提供时间倒序/关键词检索。"""

    def __init__(self, collection: _AsyncCollection) -> None:
        self._collection = collection

    @classmethod
    def from_uri(
        cls,
        uri: str,
        database: str = DATABASE_NAME,
    ) -> MidTermMemory:
        """按 URI 创建 pymongo 异步客户端。"""
        client: AsyncMongoClient[dict[str, object]] = AsyncMongoClient(
            uri,
            serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
        )
        collection = cast(_AsyncCollection, client[database][COLLECTION_NAME])
        return cls(collection)

    async def ensure_indexes(self) -> bool:
        """幂等创建 (session_id, created_at desc) 复合索引。"""
        try:
            existing = await self._collection.index_information()
            if INDEX_NAME in existing:
                return True
            await self._collection.create_index(
                [("session_id", 1), ("created_at", -1)],
                name=INDEX_NAME,
            )
            return True
        except Exception:
            _degraded("ensure_indexes")
            return False

    async def append_round(
        self,
        session_id: str,
        round_: StoredRound,
        created_at: datetime | None = None,
    ) -> bool:
        """响应后异步写入；失败只告警。"""
        try:
            document = {
                "session_id": session_id,
                "round_id": round_.round_id,
                "messages": [message.model_dump(mode="json") for message in round_.messages],
                "truncated": round_.truncated,
                "termination_reason": round_.termination_reason,
                "created_at": created_at or datetime.now(UTC),
            }
            await self._collection.insert_one(document)
            return True
        except Exception:
            _degraded("append_round")
            return False

    async def search_rounds(
        self,
        session_id: str,
        keyword: str | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        include_private: bool = False,
    ) -> list[StoredRound]:
        """按 session 过滤、时间倒序返回；默认剥离 reasoning。"""
        if not session_id.strip() or limit <= 0:
            return []
        query: dict[str, object] = {"session_id": session_id}
        if keyword:
            query["messages.content"] = {"$regex": re.escape(keyword), "$options": "i"}
        try:
            cursor = self._collection.find(query).sort("created_at", -1).limit(limit)
            documents = await cursor.to_list(length=limit)
            return [_decode_document(item, include_private=include_private) for item in documents]
        except Exception:
            _degraded("search_rounds")
            return []


def _decode_document(document: dict[str, object], include_private: bool) -> StoredRound:
    messages = []
    for item in cast(list[dict[str, object]], document["messages"]):
        message = Message.model_validate(item)
        if not include_private and message.reasoning_content is not None:
            message = message.model_copy(update={"reasoning_content": None})
        messages.append(message)
    return StoredRound(
        round_id=cast(str, document["round_id"]),
        messages=tuple(messages),
        truncated=bool(document.get("truncated")),
        termination_reason=cast(str | None, document.get("termination_reason")),
    )


def _degraded(operation: str) -> None:
    LOGGER.warning(
        "memory.degraded",
        extra={"event": "memory.degraded", "operation": operation},
    )
