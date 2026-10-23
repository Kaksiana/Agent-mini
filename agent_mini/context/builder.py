"""S15/S16 上下文拼接、预算与整轮裁剪。"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from agent_mini.context.token_counter import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    TokenCounter,
    compute_budget,
)
from agent_mini.context.window import ContextTooLarge, FitInput, TrimReason, fit_rounds
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
    """请求消息、工具快照、预算分项与裁剪统计。"""

    messages: tuple[Message, ...]
    tools_snapshot: tuple[ToolSchema, ...]
    message_tokens: int
    tool_schema_tokens: int
    protocol_overhead_tokens: int
    estimated_input_tokens: int
    budget: int
    rounds_before: int
    rounds_after: int
    tokens_before: int
    tokens_after: int
    dropped_rounds: int
    trim_reason: TrimReason | None


class ContextBuilder:
    """按固定顺序拼接、计数并整轮裁剪。"""

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
        """首次构建；当前轮仅含当前 user。"""
        return await self.fit(request, [Message(role="user", content=request.user_input)])

    async def fit(
        self,
        request: BuildRequest,
        current_messages: Sequence[Message] | None = None,
    ) -> ContextPayload:
        """按最后一条 user 识别当前轮，裁剪此前历史。"""
        current = _current_round(current_messages, request.user_input)
        prefix = _prefix(request)
        rounds = await self._load_rounds(
            request.session_id,
            request.short_term,
            request.mid_term,
        )
        tools_snapshot = tuple(request.tools_snapshot)
        result = fit_rounds(
            rounds,
            FitInput(
                prefix=prefix,
                current=current,
                tools_snapshot=tools_snapshot,
                counter=self._counter,
                budget=compute_budget(
                    self._max_context_tokens,
                    self._max_output_tokens,
                ),
                include_reasoning=request.include_reasoning,
            ),
        )
        return ContextPayload(
            messages=result.messages,
            tools_snapshot=tools_snapshot,
            message_tokens=result.message_tokens,
            tool_schema_tokens=result.tool_schema_tokens,
            protocol_overhead_tokens=result.protocol_overhead_tokens,
            estimated_input_tokens=result.tokens_after,
            budget=result.budget,
            rounds_before=result.rounds_before,
            rounds_after=result.rounds_after,
            tokens_before=result.tokens_before,
            tokens_after=result.tokens_after,
            dropped_rounds=result.dropped_rounds,
            trim_reason=result.trim_reason,
        )

    async def _load_rounds(
        self,
        session_id: str | None,
        short_term: ShortTermStore | None,
        mid_term: MidTermStore | None,
    ) -> list[StoredRound]:
        if session_id is None or not valid_session_id(session_id):
            return []
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


def _prefix(request: BuildRequest) -> list[Message]:
    messages: list[Message] = []
    if request.system_prompt:
        messages.append(Message(role="system", content=request.system_prompt))
    if request.tool_summary:
        messages.append(Message(role="system", content=request.tool_summary))
    if request.mid_term_summary:
        messages.append(Message(role="system", content=request.mid_term_summary))
    return messages


def _current_round(
    current_messages: Sequence[Message] | None,
    user_input: str,
) -> list[Message]:
    if not current_messages:
        return [Message(role="user", content=user_input)]
    for index in range(len(current_messages) - 1, -1, -1):
        if current_messages[index].role == "user":
            return list(current_messages[index:])
    return [Message(role="user", content=user_input)]


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


__all__ = ["BuildRequest", "ContextBuilder", "ContextPayload", "ContextTooLarge"]
