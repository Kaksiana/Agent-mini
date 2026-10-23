"""S16 双触发整轮裁剪。"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from agent_mini.context.token_counter import TokenCounter
from agent_mini.llm.models import Message, ToolSchema
from agent_mini.memory.base import StoredRound

DEFAULT_MAX_ROUNDS = 10
CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
CONTEXT_TOO_LARGE_STATUS = 400
TRIM_EVENT = "context.trimmed"
TrimReason = Literal["rounds", "tokens", "both"]
LOGGER = logging.getLogger("agent_mini.context")


class ContextTooLarge(Exception):
    """最小集合仍超预算的本地错误。"""

    def __init__(self, steps: int = 1) -> None:
        super().__init__("上下文仍超过预算")
        self.code = CONTEXT_TOO_LARGE
        self.http_status = CONTEXT_TOO_LARGE_STATUS
        self.steps = steps
        self.truncated = True


@dataclass(frozen=True)
class FitInput:
    """一次裁剪的固定输入。"""

    prefix: Sequence[Message]
    current: Sequence[Message]
    tools_snapshot: Sequence[ToolSchema]
    counter: TokenCounter
    budget: int
    include_reasoning: bool


@dataclass(frozen=True)
class TrimResult:
    """裁剪后的消息与可追溯分项。"""

    messages: tuple[Message, ...]
    rounds_before: int
    rounds_after: int
    tokens_before: int
    tokens_after: int
    dropped_rounds: int
    trim_reason: TrimReason | None
    message_tokens: int
    tool_schema_tokens: int
    protocol_overhead_tokens: int
    budget: int


def fit_rounds(history: Sequence[StoredRound], spec: FitInput) -> TrimResult:
    """整轮丢弃最旧历史，直到轮次与 token 均满足。"""
    tools = tuple(spec.tools_snapshot)
    remaining = list(history)
    messages = _compose(spec.prefix, remaining, spec.current)
    initial = spec.counter.count_request(messages, tools, spec.include_reasoning)
    if _fixed_exceeds(spec, tools):
        raise ContextTooLarge()
    reason: TrimReason | None = None
    while remaining:
        over_rounds = len(remaining) > DEFAULT_MAX_ROUNDS
        over_tokens = initial.estimated_input_tokens > spec.budget
        if not (over_rounds or over_tokens):
            break
        reason = _reason(over_rounds, over_tokens)
        remaining.pop(0)
        messages = _compose(spec.prefix, remaining, spec.current)
        initial = spec.counter.count_request(messages, tools, spec.include_reasoning)
    if initial.estimated_input_tokens > spec.budget:
        raise ContextTooLarge()
    tokens_before = spec.counter.count_request(
        _compose(spec.prefix, history, spec.current),
        tools,
        spec.include_reasoning,
    ).estimated_input_tokens
    result = TrimResult(
        messages=tuple(messages),
        rounds_before=len(history),
        rounds_after=len(remaining),
        tokens_before=tokens_before,
        tokens_after=initial.estimated_input_tokens,
        dropped_rounds=len(history) - len(remaining),
        trim_reason=reason,
        message_tokens=initial.message_tokens,
        tool_schema_tokens=initial.tool_schema_tokens,
        protocol_overhead_tokens=initial.protocol_overhead_tokens,
        budget=spec.budget,
    )
    if result.dropped_rounds:
        LOGGER.info(
            TRIM_EVENT,
            extra={
                "event": TRIM_EVENT,
                "rounds_before": result.rounds_before,
                "rounds_after": result.rounds_after,
                "dropped_rounds": result.dropped_rounds,
                "tokens_before": result.tokens_before,
                "tokens_after": result.tokens_after,
                "trim_reason": result.trim_reason,
            },
        )
    return result


def _compose(
    prefix: Sequence[Message],
    history: Sequence[StoredRound],
    current: Sequence[Message],
) -> list[Message]:
    messages = list(prefix)
    for round_ in history:
        messages.extend(round_.messages)
    messages.extend(current)
    return messages


def _fixed_exceeds(spec: FitInput, tools: Sequence[ToolSchema]) -> bool:
    counts = spec.counter.count_request(
        list(spec.prefix) + list(spec.current),
        tools,
        spec.include_reasoning,
    )
    return counts.estimated_input_tokens > spec.budget


def _reason(over_rounds: bool, over_tokens: bool) -> TrimReason:
    if over_rounds and over_tokens:
        return "both"
    return "rounds" if over_rounds else "tokens"
