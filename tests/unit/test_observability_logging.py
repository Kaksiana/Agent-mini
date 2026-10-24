"""TC-L1-020、TC-L5-004：结构化日志与脱敏。"""

from __future__ import annotations

import asyncio
import io
import json
import logging

import pytest

from agent_mini.observability.logging import (
    FIXED_FIELDS,
    JsonFormatter,
    RedactionFilter,
    set_trace_context,
)

pytestmark = pytest.mark.unit


def _capture() -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    logger = logging.getLogger("agent_mini.test")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, stream


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def test_fixed_fields_and_json_lines() -> None:
    logger, stream = _capture()
    set_trace_context("trace-1", "session-A")
    logger.info("react.step", extra={"event": "react.step", "step": 2, "duration_ms": 7})

    lines = _lines(stream)
    assert len(lines) == 1
    assert set(FIXED_FIELDS) <= set(lines[0])
    assert lines[0]["trace_id"] == "trace-1"
    assert lines[0]["session_id"] == "session-A"
    assert lines[0]["event"] == "react.step"
    assert lines[0]["duration_ms"] == 7


async def test_trace_id_survives_create_task() -> None:
    logger, stream = _capture()
    set_trace_context("trace-task", "session-A")

    async def child() -> None:
        await asyncio.sleep(0)
        logger.warning("memory.degraded", extra={"event": "memory.degraded"})

    await asyncio.create_task(child())
    lines = _lines(stream)
    assert lines[0]["trace_id"] == "trace-task"


def test_redaction_of_secrets_and_reasoning() -> None:
    logger, stream = _capture()
    set_trace_context("trace-2", "session-A")
    logger.info(
        "Bearer xyz sk-other1234",
        extra={
            "event": "llm.call",
            "api_key": "sk-sentinel123456",
            "authorization": "Bearer abc",
            "password": "secret",
            "reasoning_content": "private reasoning",
            "content": "full prompt body",
            "prompt": "full prompt",
            "details": [{"api_key": "plain-secret"}],
        },
    )

    text = stream.getvalue()
    assert "sk-sentinel" not in text
    assert "Bearer abc" not in text
    assert "private reasoning" not in text
    assert "full prompt" not in text
    assert "plain-secret" not in text
    assert "***" in text
    lines = _lines(stream)
    assert lines[0]["reasoning_content"] == "***"
    content = lines[0]["content"]
    assert isinstance(content, str)
    assert content.startswith("<redacted:")


def test_secret_value_in_message_is_redacted() -> None:
    logger, stream = _capture()
    logger.warning("auth failed password=hunter2 Bearer token123")

    text = stream.getvalue()
    assert "hunter2" not in text
    assert "token123" not in text
    assert "***" in text


def test_configure_logging_disables_propagation_and_old_handlers() -> None:
    from agent_mini.observability.logging import _JsonHandler, configure_logging

    logger = logging.getLogger("agent_mini")
    stale = logging.StreamHandler(io.StringIO())
    logger.addHandler(stale)
    configure_logging()
    assert logger.propagate is False
    assert stale not in logger.handlers
    assert any(isinstance(handler, _JsonHandler) for handler in logger.handlers)
