"""S15 本地 token 计数与预算计算。"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from agent_mini.llm.models import Message, ToolSchema

ENCODING_NAME = "cl100k_base"
DEFAULT_PROTOCOL_OVERHEAD_TOKENS = 256
DEFAULT_MAX_OUTPUT_TOKENS = 1024
SAFETY_MARGIN_RATIO = 0.10
ASCII_TOKENS_PER_CHAR = 0.3
NON_ASCII_TOKENS_PER_CHAR = 0.6
JSON_ENSURE_ASCII = False
JSON_SORT_KEYS = True
JSON_SEPARATORS = (",", ":")
LOGGER = logging.getLogger("agent_mini.context")


class _Encoder(Protocol):
    def encode(self, text: str) -> list[int]: ...


@dataclass(frozen=True)
class TokenCounts:
    """一次请求的 token 分项。"""

    message_tokens: int
    tool_schema_tokens: int
    protocol_overhead_tokens: int
    estimated_input_tokens: int


class TokenCounter:
    """tiktoken 计数；不可用时按字符比例降级。"""

    def __init__(
        self,
        encoder: _Encoder | None = None,
        protocol_overhead_tokens: int = DEFAULT_PROTOCOL_OVERHEAD_TOKENS,
    ) -> None:
        self._encoder = encoder
        self._protocol_overhead_tokens = protocol_overhead_tokens
        self._degraded = False

    def count_request(
        self,
        messages: Sequence[Message],
        tools_snapshot: Sequence[ToolSchema],
    ) -> TokenCounts:
        """统计 messages 与完整 tools Schema，加入协议开销。"""
        if not messages and not tools_snapshot:
            return TokenCounts(0, 0, 0, 0)
        message_payload = [message.to_provider(include_reasoning=True) for message in messages]
        tool_payload = [tool.to_provider() for tool in tools_snapshot]
        message_tokens = self._count_json(message_payload)
        tool_tokens = self._count_json(tool_payload)
        overhead = self._protocol_overhead_tokens
        return TokenCounts(
            message_tokens=message_tokens,
            tool_schema_tokens=tool_tokens,
            protocol_overhead_tokens=overhead,
            estimated_input_tokens=message_tokens + tool_tokens + overhead,
        )

    def _count_json(self, payload: object) -> int:
        text = canonical_json(payload)
        encoder = self._get_encoder()
        if encoder is not None:
            return len(encoder.encode(text))
        return _char_estimate(text)

    def _get_encoder(self) -> _Encoder | None:
        if self._encoder is not None:
            return self._encoder
        try:
            self._encoder = _load_encoder(ENCODING_NAME)
        except Exception:
            if not self._degraded:
                self._degraded = True
                LOGGER.warning(
                    "token_counter.degraded",
                    extra={"event": "token_counter.degraded"},
                )
            return None
        return self._encoder


def canonical_json(payload: object) -> str:
    """规范 JSON：保证乱序字典与多次调用可复现。"""
    return json.dumps(
        payload,
        ensure_ascii=JSON_ENSURE_ASCII,
        sort_keys=JSON_SORT_KEYS,
        separators=JSON_SEPARATORS,
    )


def compute_budget(
    max_context_tokens: int,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> int:
    """预算 = 上下文上限 - 输出预留 - 10% 安全余量。"""
    safety = math.floor(max_context_tokens * SAFETY_MARGIN_RATIO)
    return max_context_tokens - max_output_tokens - safety


def _load_encoder(name: str) -> _Encoder:
    import tiktoken

    return cast(_Encoder, tiktoken.get_encoding(name))


def _char_estimate(text: str) -> int:
    ascii_count = sum(1 for char in text if ord(char) < 128)
    non_ascii_count = len(text) - ascii_count
    return math.ceil(ascii_count * ASCII_TOKENS_PER_CHAR) + math.ceil(
        non_ascii_count * NON_ASCII_TOKENS_PER_CHAR
    )
