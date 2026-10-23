"""TC-L3-009/010/011/012：系统数据库五表与异步写入。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import text

from agent_mini.llm.models import LLMResponse, Message, Usage
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.result import AgentResult
from agent_mini.systemdb.models import (
    ModelRecord,
    RequestMetricsRecord,
    SystemDBConfig,
    ToolInvocationRecord,
    ToolRecord,
)
from agent_mini.systemdb.repository import SystemDBRepository

pytestmark = pytest.mark.integration


def _repo(tmp_path: Path) -> SystemDBRepository:
    dsn = f"sqlite+aiosqlite:///{tmp_path / 'system.db'}"
    return SystemDBRepository(SystemDBConfig(dsn=dsn))


async def test_five_tables_idempotent(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert await repo.ensure_schema() is True
    assert await repo.ensure_schema() is True

    async with repo.engine.connect() as connection:
        rows = await connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        names = {row[0] for row in rows}
    await repo.close()

    assert {"sessions", "models", "tools", "tool_invocations", "request_metrics"} <= names


async def test_upsert_models_and_tools_preserves_enabled(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    await repo.ensure_schema()
    models = [
        ModelRecord("m1", "deepseek", "https://x", "deepseek-chat", 16_000),
        ModelRecord("m2", "deepseek", "https://x", "deepseek-reasoner", 64_000),
    ]
    tools = [ToolRecord(f"t{index}", "1.0", "desc", {"type": "object"}) for index in range(6)]
    assert await repo.upsert_models(models) is True
    assert await repo.upsert_tools(tools) is True
    async with repo.engine.begin() as connection:
        await connection.execute(text("UPDATE models SET enabled = 0 WHERE name = 'm1'"))
    assert await repo.upsert_models(models) is True

    async with repo.engine.connect() as connection:
        model_count = (await connection.execute(text("SELECT COUNT(*) FROM models"))).scalar()
        tool_count = (await connection.execute(text("SELECT COUNT(*) FROM tools"))).scalar()
        enabled = (
            await connection.execute(text("SELECT enabled FROM models WHERE name='m1'"))
        ).scalar()
    await repo.close()

    assert model_count == 2
    assert tool_count == 6
    assert enabled == 0


async def test_session_audit_metrics_and_isolation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    await repo.ensure_schema()
    assert await repo.upsert_session("A") is True
    assert await repo.upsert_session("A") is True
    assert await repo.record_tool_invocation(
        ToolInvocationRecord("A", "trace", "echo", True, None, 1, datetime.now(UTC))
    )
    assert await repo.record_metrics(
        RequestMetricsRecord("trace", "A", 2, 1, 10, 5, 3, datetime.now(UTC))
    )

    async with repo.engine.connect() as connection:
        session = (
            await connection.execute(text("SELECT message_count, status FROM sessions"))
        ).one()
        audit = (await connection.execute(text("SELECT COUNT(*) FROM tool_invocations"))).scalar()
        metrics = (await connection.execute(text("SELECT COUNT(*) FROM request_metrics"))).scalar()
        columns = await connection.execute(text("PRAGMA table_info(request_metrics)"))
        names = {row[1] for row in columns}
    await repo.close()

    assert session == (2, "active")
    assert audit == 1
    assert metrics == 1
    assert "content" not in names


async def test_degraded_on_broken_connection(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = SystemDBRepository(SystemDBConfig(dsn="sqlite+aiosqlite:////missing/dir/db.sqlite"))
    with caplog.at_level(logging.WARNING):
        assert await repo.ensure_schema() is False
    assert "systemdb.degraded" in caplog.text
    await repo.close()


class _Store:
    def __init__(self) -> None:
        self.called = False

    async def record_turn(
        self,
        session_id: str,
        result: AgentResult,
        duration_ms: int,
        trace_id: str,
    ) -> bool:
        self.called = True
        return True


class _LLM:
    async def chat(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        **params: object,
    ) -> LLMResponse:
        return LLMResponse(
            content="ok",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_agent_system_write_is_async() -> None:
    store = _Store()
    agent = Agent(cast(Any, _LLM())).with_system_db(cast(Any, store), 1.0)

    result = await agent.run("hi", session_id="A")
    await agent.drain()

    assert result.reply == "ok"
    assert store.called is True
