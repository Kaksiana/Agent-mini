"""Memory 短时存储协议与冻结轮次模型。"""

from dataclasses import dataclass
from typing import Protocol

from agent_mini.llm.models import Message

MAX_SESSION_ID_LENGTH = 128


def valid_session_id(session_id: str) -> bool:
    """会话 ID 必须非空白且不超过 128 字符。"""
    return bool(session_id.strip()) and len(session_id) <= MAX_SESSION_ID_LENGTH


@dataclass(frozen=True)
class StoredRound:
    """Redis 中一个完整轮次的公开结构。"""

    round_id: str
    messages: tuple[Message, ...]
    truncated: bool = False
    termination_reason: str | None = None


class ShortTermStore(Protocol):
    """S13 短时窗口最小接口；S14+ 可扩展。"""

    async def append_round(
        self,
        session_id: str,
        messages: list[Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        """写回一个完整轮次；失败返回 False。"""
        ...

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        """读取最近完整轮次，时间正序。"""
        ...


class MidTermStore(Protocol):
    """S14 中期存储最小接口，供 Runtime 依赖。"""

    async def append_round(
        self,
        session_id: str,
        round_: StoredRound,
    ) -> bool:
        """持久化一个完整轮次；失败返回 False。"""
        ...

    async def drain(self) -> None:
        """等待内部待写任务完成。"""
        ...

    async def get_rounds(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[StoredRound]:
        """读取会话轮次，时间正序，私有 reasoning 保留。"""
        ...
