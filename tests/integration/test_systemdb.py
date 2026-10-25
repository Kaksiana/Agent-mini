"""TC-L3-009/010/011/012：系统数据库五表与异步写入。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import text

from agent_mini.llm.models import LLMResponse, Message, ToolCall, Usage
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.runtime.result import AgentResult
from agent_mini.systemdb.models import (
    ModelRecord,
    RequestMetricsRecord,
    SystemDBConfig,
    ToolInvocationRecord,
    ToolRecord,
)
from agent_mini.systemdb.repository import SystemDBRepository
from agent_mini.tools import builtin as _builtin
from agent_mini.tools.registry import DEFAULT_REGISTRY

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
        self.duration_ms = -1

    async def record_turn(
        self,
        session_id: str,
        result: AgentResult,
        duration_ms: int,
        trace_id: str,
    ) -> bool:
        self.called = True
        self.duration_ms = duration_ms
        return True


class _LLM:
    async def chat(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        **params: object,
    ) -> LLMResponse:
        await __import__("asyncio").sleep(0.02)
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
    assert store.duration_ms >= 10


async def test_initialize_and_status_transitions(tmp_path: Path) -> None:
    dsn = f"sqlite+aiosqlite:///{tmp_path / 'status.db'}"
    repo = SystemDBRepository(SystemDBConfig(dsn=dsn, auto_create=True))
    assert (
        await repo.initialize(
            [ModelRecord("m1", "p", "u", "m", 100)],
            [ToolRecord("t1", "1", "d", {})],
        )
        is True
    )
    assert await repo.set_session_status("A", "idle") is False
    assert await repo.upsert_session("A") is True
    assert await repo.set_session_status("A", "idle") is True
    assert await repo.upsert_session("A") is True
    async with repo.engine.connect() as connection:
        status = (
            await connection.execute(text("SELECT status FROM sessions WHERE session_id='A'"))
        ).scalar()
    assert status == "idle"
    assert await repo.set_session_status("A", "active") is True
    await repo.close()


async def test_created_at_is_stable_on_upsert(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    await repo.ensure_schema()
    model = ModelRecord("m1", "p", "u", "m", 100)
    await repo.upsert_models([model])
    async with repo.engine.connect() as connection:
        first = (
            await connection.execute(text("SELECT created_at FROM models WHERE name='m1'"))
        ).scalar()
    await repo.upsert_models([model])
    async with repo.engine.connect() as connection:
        second = (
            await connection.execute(text("SELECT created_at FROM models WHERE name='m1'"))
        ).scalar()
    await repo.close()
    assert first == second


@pytest.mark.skipif(
    not __import__("os").environ.get("MYSQL_TEST_DSN"),
    reason="MYSQL_TEST_DSN not configured (ISSUE-043)",
)
async def test_real_mysql_schema_when_configured() -> None:
    repo = SystemDBRepository(
        SystemDBConfig(dsn=__import__("os").environ["MYSQL_TEST_DSN"], auto_create=True)
    )
    assert await repo.ensure_schema() is True
    assert await repo.ensure_schema() is True
    async with repo.engine.connect() as connection:
        rows = await connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
        )
        names = {row[0] for row in rows}
    await repo.close()
    assert {"sessions", "models", "tools", "tool_invocations", "request_metrics"} <= names


class _ToolLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "2+2"})],
                finish_reason="tool_calls",
                usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        return LLMResponse(
            content="4",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_real_repository_five_table_chain(tmp_path: Path) -> None:
    _ = _builtin
    repo = _repo(tmp_path)
    assert await repo.ensure_schema()
    agent = Agent(
        cast(Any, _ToolLLM()),
        tool_executor=RegistryExecutor(DEFAULT_REGISTRY),
    ).with_system_db(repo, 1.0)
    result = await agent.run("calc", session_id="chain", trace_id="trace-chain")
    await agent.drain()
    assert result.tool_calls == 1
    assert result.trace_id == "trace-chain"
    async with repo.engine.connect() as connection:
        counts = {}
        for table in ("sessions", "tool_invocations", "request_metrics"):
            counts[table] = (
                await connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
            ).scalar()
    await repo.close()
    assert counts == {"sessions": 1, "tool_invocations": 1, "request_metrics": 1}
