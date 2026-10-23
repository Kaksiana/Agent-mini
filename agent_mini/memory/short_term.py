"""S13 Redis 短时会话窗口。"""

import json
import logging
from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis

from agent_mini.llm.models import Message

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
        self._client = client
        self._max_rounds = max_rounds
        self._ttl_seconds = ttl_seconds

    def key(self, session_id: str) -> str:
        """返回含 session_id 的 Redis key。"""
        return f"{KEY_PREFIX}:{session_id}:rounds"

    async def append_round(
        self,
        session_id: str,
        messages: list[Message],
        round_id: str,
    ) -> bool:
        """同步写回完整轮次；异常降级为 False。"""
        try:
            payload = _encode_round(round_id, messages)
            key = self.key(session_id)
            await cast(Awaitable[int], self._client.rpush(key, payload))
            await cast(Awaitable[str], self._client.ltrim(key, -self._max_rounds, -1))
            await cast(Awaitable[bool], self._client.expire(key, self._ttl_seconds))
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
    ) -> list[list[Message]]:
        """读取最近完整轮次；异常/解析失败降级为空。"""
        count = self._max_rounds if limit is None else limit
        if count <= 0:
            return []
        try:
            raw = await cast(
                Awaitable[list[Any]],
                self._client.lrange(self.key(session_id), -count, -1),
            )
            return [_decode_round(item) for item in raw]
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )
            return []


def _encode_round(round_id: str, messages: list[Message]) -> str:
    payload = {
        "round_id": round_id,
        "messages": [message.model_dump(mode="json") for message in messages],
    }
    return json.dumps(payload, ensure_ascii=False)


def _decode_round(raw: str | bytes) -> list[Message]:
    data: Any = json.loads(raw)
    return [Message.model_validate(item) for item in data["messages"]]
