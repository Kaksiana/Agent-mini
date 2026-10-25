"""S13 Redis 短时会话窗口。"""

import json
import logging
from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis

from agent_mini.llm.models import Message
from agent_mini.memory.base import StoredRound, valid_session_id

DEFAULT_MAX_ROUNDS = 10
DEFAULT_TTL_SECONDS = 86_400
KEY_PREFIX = "agent_mini:short_term"
LOGGER = logging.getLogger("agent_mini.memory")


class ShortTermMemory:
    """按完整轮次存 Redis List，按整轮 LTRIM + TTL。"""

    def __init__(
        self,
        client: Redis,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        if isinstance(max_rounds, bool) or max_rounds <= 0:
            raise ValueError("max_rounds 必须是正整数")
        if isinstance(ttl_seconds, bool) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds 必须是正整数")
        self._client = client
        self._max_rounds = max_rounds
        self._ttl_seconds = ttl_seconds

    def key(self, session_id: str) -> str:
        """返回含 session_id 的 Redis key。"""
        return f"{KEY_PREFIX}:{session_id}:rounds"

    async def close(self) -> None:
        """关闭 Redis 客户端。"""
        await self._client.aclose()

    async def append_round(
        self,
        session_id: str,
        messages: list[Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        """同步写回完整轮次；异常降级为 False。"""
        if not valid_session_id(session_id):
            return False
        try:
            stored = StoredRound(round_id, tuple(messages), truncated, termination_reason)
            payload = _encode_round(stored)
            key = self.key(session_id)
            pipeline = self._client.pipeline(transaction=True)
            pipeline.rpush(key, payload)
            pipeline.ltrim(key, -self._max_rounds, -1)
            pipeline.expire(key, self._ttl_seconds)
            await cast(Awaitable[Any], pipeline.execute())
            return True
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )
            return False

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        """读取最近完整轮次；异常/解析失败降级为空。"""
        count = self._max_rounds if limit is None else limit
        if count <= 0 or not valid_session_id(session_id):
            return []
        try:
            raw = await cast(
                Awaitable[list[Any]],
                self._client.lrange(self.key(session_id), -count, -1),
            )
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )
            return []
        rounds: list[StoredRound] = []
        for item in raw:
            try:
                rounds.append(_decode_round(item))
            except Exception:
                LOGGER.warning(
                    "memory.corrupt_round",
                    extra={"event": "memory.corrupt_round", "session_id": session_id},
                )
        return rounds


def _encode_round(round_: StoredRound) -> str:
    payload = {
        "round_id": round_.round_id,
        "truncated": round_.truncated,
        "termination_reason": round_.termination_reason,
        "messages": [message.model_dump(mode="json") for message in round_.messages],
    }
    return json.dumps(payload, ensure_ascii=False)


def _decode_round(raw: str | bytes) -> StoredRound:
    data: Any = json.loads(raw)
    messages = tuple(Message.model_validate(item) for item in data["messages"])
    return StoredRound(
        round_id=data["round_id"],
        messages=messages,
        truncated=bool(data.get("truncated", False)),
        termination_reason=data.get("termination_reason"),
    )


def _valid_session(session_id: str) -> bool:
    return valid_session_id(session_id)
