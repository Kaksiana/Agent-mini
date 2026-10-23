"""S19 结构化 JSON 日志与统一脱敏。"""

from __future__ import annotations

import contextvars
import json
import logging
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id",
    default=None,
)
SESSION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id",
    default=None,
)
FIXED_FIELDS = ("ts", "level", "event", "trace_id", "session_id", "step", "duration_ms")
SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "password", "cookie", "reasoning_content"}
)
CONTENT_KEYS = frozenset({"content", "prompt", "arguments", "tool_arguments"})
REDACTED = "***"
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{4,}\b"),
    re.compile(
        r"(?i)([\"']?(authorization|api[_-]?key|password|cookie)[\"']?\s*[:=]\s*)"
        r"([\"']?)[^\s,}\]]+"
    ),
)


def set_trace_context(trace_id: str | None, session_id: str | None = None) -> None:
    """设置当前异步上下文 trace/session。"""
    TRACE_ID.set(trace_id)
    SESSION_ID.set(session_id)


def current_trace_id() -> str | None:
    """读取当前 trace_id。"""
    return TRACE_ID.get()


def reset_trace_context() -> None:
    """清空当前异步上下文 trace/session。"""
    TRACE_ID.set(None)
    SESSION_ID.set(None)


class JsonFormatter(logging.Formatter):
    """固定字段 + 事件附加字段的 JSON Lines。"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化固定字段与附加字段。"""
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "trace_id": getattr(record, "trace_id", None) or TRACE_ID.get(),
            "session_id": getattr(record, "session_id", None) or SESSION_ID.get(),
            "step": getattr(record, "step", 0),
            "duration_ms": getattr(record, "duration_ms", 0),
        }
        for key, value in record.__dict__.items():
            if key in payload or key in _STANDARD_LOG_ATTRS:
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class RedactionFilter(logging.Filter):
    """唯一脱敏点：过滤字段、文本与 reasoning/content。"""

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤秘密、reasoning 与完整内容。"""
        record.event = redact_text(str(getattr(record, "event", record.msg)))
        record.msg = redact_text(record.getMessage())
        record.args = ()
        for key, value in list(record.__dict__.items()):
            if key in _STANDARD_LOG_ATTRS or key == "event":
                continue
            record.__dict__[key] = _sanitize_field(key, value)
        return True


def redact_text(value: str) -> str:
    """对任意文本应用秘密正则。"""
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(REDACTED, result)
    return result


def _sanitize_field(key: str, value: object) -> object:
    lowered = key.lower()
    if lowered in SENSITIVE_KEYS:
        return REDACTED
    if lowered in CONTENT_KEYS:
        return f"<redacted:{len(str(value))}>"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            item_key: _sanitize_field(str(item_key), item_value)
            for item_key, item_value in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_sanitize_field(str(key), item) for key, item in enumerate(value)]
    if isinstance(value, BaseException):
        return redact_text(str(value))
    return value


class _JsonHandler(logging.StreamHandler[Any]):
    """带标记的 JSON handler，供幂等安装识别。"""


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """幂等安装 JSON handler 与脱敏 filter。"""
    logger = logging.getLogger("agent_mini")
    logger.setLevel(level)
    if not any(isinstance(handler, _JsonHandler) for handler in logger.handlers):
        handler = _JsonHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RedactionFilter())
        logger.addHandler(handler)
    return logger


_STANDARD_LOG_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
    }
)
