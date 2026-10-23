"""Memory 短时存储协议。"""

from typing import Protocol

from agent_mini.llm.models import Message


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
    ) -> list[list[Message]]:
        """读取最近完整轮次，时间正序。"""
        ...
