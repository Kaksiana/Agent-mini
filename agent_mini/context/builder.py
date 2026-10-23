"""S15 上下文拼接与 token 预算。"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from agent_mini.context.token_counter import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    TokenCounter,
    compute_budget,
)
from agent_mini.llm.models import Message, ToolSchema
from agent_mini.memory.base import (
    MidTermStore,
    ShortTermStore,
    StoredRound,
    valid_session_id,
)

DEFAULT_HISTORY_LIMIT = 100
DEFAULT_READ_TIMEOUT_SECONDS = 1.0
LOGGER = logging.getLogger("agent_mini.context")


@dataclass(frozen=True)
class BuildRequest:
    """一次 Context 组装所需的输入。"""

    user_input: str
    tools_snapshot: Sequence[ToolSchema]
    session_id: str | None = None
    short_term: ShortTermStore | None = None
    mid_term: MidTermStore | None = None
    system_prompt: str | None = None
    tool_summary: str | None = None
    mid_term_summary: str | None = None
    include_reasoning: bool = True


@dataclass(frozen=True)
class ContextPayload:
    """S15 的请求消息、工具快照与预算分项。"""

    messages: tuple[Message, ...]
    tools_snapshot: tuple[ToolSchema, ...]
    message_tokens: int
    tool_schema_tokens: int
    protocol_overhead_tokens: int
    estimated_input_tokens: int
    budget: int


class ContextBuilder:
    """按固定顺序拼接并计数；不做任何裁剪。"""

    def __init__(
        self,
        token_counter: TokenCounter,
        max_context_tokens: int,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
    ) -> None:
        self._counter = token_counter
        self._max_context_tokens = max_context_tokens
        self._max_output_tokens = max_output_tokens
        self._read_timeout = read_timeout_seconds

    async def build(self, request: BuildRequest) -> ContextPayload:
        """拼接 system、可选摘要、历史 StoredRound、当前 user。"""
        messages: list[Message] = []
        if request.system_prompt:
            messages.append(Message(role="system", content=request.system_prompt))
        if request.tool_summary:
            messages.append(Message(role="system", content=request.tool_summary))
        if request.mid_term_summary:
            messages.append(Message(role="system", content=request.mid_term_summary))
        messages.extend(
            await self._history_messages(
                request.session_id,
                request.short_term,
                request.mid_term,
            )
        )
        messages.append(Message(role="user", content=request.user_input))
        tools_snapshot = tuple(request.tools_snapshot)
        counts = self._counter.count_request(
            messages,
            tools_snapshot,
            include_reasoning=request.include_reasoning,
        )
        return ContextPayload(
            messages=tuple(messages),
            tools_snapshot=tools_snapshot,
            message_tokens=counts.message_tokens,
            tool_schema_tokens=counts.tool_schema_tokens,
            protocol_overhead_tokens=counts.protocol_overhead_tokens,
            estimated_input_tokens=counts.estimated_input_tokens,
            budget=compute_budget(self._max_context_tokens, self._max_output_tokens),
        )

    async def _history_messages(
        self,
        session_id: str | None,
        short_term: ShortTermStore | None,
        mid_term: MidTermStore | None,
    ) -> list[Message]:
        if session_id is None or not valid_session_id(session_id):
            return []
        rounds = await self._load_rounds(session_id, short_term, mid_term)
        messages: list[Message] = []
        for stored in rounds:
            messages.extend(stored.messages)
        return messages

    async def _load_rounds(
        self,
        session_id: str,
        short_term: ShortTermStore | None,
        mid_term: MidTermStore | None,
    ) -> list[StoredRound]:
        rounds: list[StoredRound] = []
        if mid_term is not None:
            rounds.extend(await self._read_mid_term(mid_term, session_id))
        seen: set[str] = set()
        deduped: list[StoredRound] = []
        _append_unique(rounds, seen, deduped)
        if short_term is not None:
            recent = await self._read_short_term(short_term, session_id)
            _append_unique(recent, seen, deduped)
        return deduped

    async def _read_mid_term(
        self,
        mid_term: MidTermStore,
        session_id: str,
    ) -> list[StoredRound]:
        try:
            return await asyncio.wait_for(
                mid_term.get_rounds(session_id, DEFAULT_HISTORY_LIMIT),
                self._read_timeout,
            )
        except Exception:
            _degraded("mid_term")
            return []

    async def _read_short_term(
        self,
        short_term: ShortTermStore,
        session_id: str,
    ) -> list[StoredRound]:
        try:
            return await asyncio.wait_for(
                short_term.get_recent_rounds(session_id),
                self._read_timeout,
            )
        except Exception:
            _degraded("short_term")
            return []


def _append_unique(
    source: list[StoredRound],
    seen: set[str],
    target: list[StoredRound],
) -> None:
    for stored in source:
        if stored.round_id in seen:
            continue
        seen.add(stored.round_id)
        target.append(stored)


def _degraded(source: str) -> None:
    LOGGER.warning(
        "context.degraded",
        extra={"event": "context.degraded", "source": source},
    )
