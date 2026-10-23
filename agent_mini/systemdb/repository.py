"""S17 SQLAlchemy Core 系统数据库仓储。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql import Executable

from agent_mini.runtime.result import AgentResult
from agent_mini.systemdb.models import (
    ModelRecord,
    RequestMetricsRecord,
    SystemDBConfig,
    ToolInvocationRecord,
    ToolRecord,
)

LOGGER = logging.getLogger("agent_mini.systemdb")


class SystemDBRepository:
    """五表仓储；所有写入失败只告警。"""

    def __init__(self, config: SystemDBConfig) -> None:
        self._config = config
        self.engine: AsyncEngine = create_async_engine(
            config.dsn,
            pool_size=config.pool_size,
            pool_timeout=config.pool_timeout_seconds,
        )
        self.metadata = _metadata()
        self._tables = self.metadata.tables

    async def ensure_schema(self) -> bool:
        """幂等建表。"""
        try:
            async with self.engine.begin() as connection:
                await connection.run_sync(self.metadata.create_all)
            return True
        except Exception:
            _degraded("ensure_schema")
            return False

    async def upsert_models(self, records: list[ModelRecord]) -> bool:
        """按 name 唯一键幂等 upsert；不覆盖手工 enabled。"""
        try:
            async with self.engine.begin() as connection:
                for record in records:
                    await connection.execute(self._model_upsert(record))
            return True
        except Exception:
            _degraded("upsert_models")
            return False

    async def upsert_tools(self, records: list[ToolRecord]) -> bool:
        """按 name 唯一键幂等 upsert；不覆盖手工 enabled。"""
        try:
            async with self.engine.begin() as connection:
                for record in records:
                    await connection.execute(self._tool_upsert(record))
            return True
        except Exception:
            _degraded("upsert_tools")
            return False

    async def upsert_session(self, session_id: str) -> bool:
        """首次插入，之后累加 message_count 并刷新活跃时间。"""
        now = datetime.now(UTC)
        try:
            async with self.engine.begin() as connection:
                await connection.execute(self._session_upsert(session_id, now))
            return True
        except Exception:
            _degraded("upsert_session")
            return False

    async def record_tool_invocation(self, record: ToolInvocationRecord) -> bool:
        """写入单条工具审计。"""
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    self._tables["tool_invocations"]
                    .insert()
                    .values(
                        session_id=record.session_id,
                        trace_id=record.trace_id,
                        tool_name=record.tool_name,
                        ok=record.ok,
                        error_code=record.error_code,
                        duration_ms=record.duration_ms,
                        created_at=record.created_at,
                    )
                )
            return True
        except Exception:
            _degraded("record_tool_invocation")
            return False

    async def record_metrics(self, record: RequestMetricsRecord) -> bool:
        """写入单条请求指标。"""
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    self._tables["request_metrics"]
                    .insert()
                    .values(
                        trace_id=record.trace_id,
                        session_id=record.session_id,
                        steps=record.steps,
                        tool_calls=record.tool_calls,
                        prompt_tokens=record.prompt_tokens,
                        completion_tokens=record.completion_tokens,
                        duration_ms=record.duration_ms,
                        created_at=record.created_at,
                    )
                )
            return True
        except Exception:
            _degraded("record_metrics")
            return False

    async def record_turn(
        self,
        session_id: str,
        result: AgentResult,
        duration_ms: int,
        trace_id: str,
    ) -> bool:
        """一次会话收尾：session、工具审计、请求指标。"""
        ok = await self.upsert_session(session_id)
        now = datetime.now(UTC)
        for item in result.tool_traces:
            ok = (
                await self.record_tool_invocation(
                    ToolInvocationRecord(
                        session_id=session_id,
                        trace_id=trace_id,
                        tool_name=item.tool,
                        ok=item.ok,
                        error_code=item.error_code,
                        duration_ms=duration_ms,
                        created_at=now,
                    )
                )
                and ok
            )
        return (
            await self.record_metrics(
                RequestMetricsRecord(
                    trace_id=trace_id,
                    session_id=session_id,
                    steps=result.steps,
                    tool_calls=result.tool_calls,
                    prompt_tokens=result.usage.prompt_tokens,
                    completion_tokens=result.usage.completion_tokens,
                    duration_ms=duration_ms,
                    created_at=now,
                )
            )
            and ok
        )

    async def close(self) -> None:
        """释放连接池。"""
        await self.engine.dispose()

    def _model_upsert(self, record: ModelRecord) -> Executable:
        table = self._tables["models"]
        now = datetime.now(UTC)
        values = {
            "name": record.name,
            "provider": record.provider,
            "base_url": record.base_url,
            "model": record.model,
            "max_context_tokens": record.max_context_tokens,
            "enabled": record.enabled,
            "created_at": now,
            "updated_at": now,
        }
        if self._is_sqlite():
            return cast(
                Executable,
                sqlite_insert(table)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={key: values[key] for key in values if key != "enabled"},
                ),
            )
        return cast(
            Executable,
            mysql_insert(table)
            .values(**values)
            .on_duplicate_key_update(**{key: values[key] for key in values if key != "enabled"}),
        )

    def _tool_upsert(self, record: ToolRecord) -> Executable:
        table = self._tables["tools"]
        now = datetime.now(UTC)
        values = {
            "name": record.name,
            "version": record.version,
            "description": record.description,
            "params_schema": record.params_schema,
            "enabled": record.enabled,
            "created_at": now,
            "updated_at": now,
        }
        if self._is_sqlite():
            return cast(
                Executable,
                sqlite_insert(table)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["name"],
                    set_={key: values[key] for key in values if key != "enabled"},
                ),
            )
        return cast(
            Executable,
            mysql_insert(table)
            .values(**values)
            .on_duplicate_key_update(**{key: values[key] for key in values if key != "enabled"}),
        )

    def _session_upsert(self, session_id: str, now: datetime) -> Executable:
        table = self._tables["sessions"]
        values = {
            "session_id": session_id,
            "status": "active",
            "created_at": now,
            "last_active_at": now,
            "message_count": 1,
            "meta": {},
        }
        if self._is_sqlite():
            return cast(
                Executable,
                sqlite_insert(table)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["session_id"],
                    set_={
                        "last_active_at": now,
                        "status": "active",
                        "message_count": table.c.message_count + 1,
                    },
                ),
            )
        return cast(
            Executable,
            mysql_insert(table)
            .values(**values)
            .on_duplicate_key_update(
                last_active_at=now,
                status="active",
                message_count=table.c.message_count + 1,
            ),
        )

    def _is_sqlite(self) -> bool:
        return self.engine.dialect.name == "sqlite"


def _metadata() -> MetaData:
    metadata = MetaData()
    Table(
        "sessions",
        metadata,
        Column("session_id", String(128), primary_key=True),
        Column("status", String(16), nullable=False, default="active"),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("last_active_at", DateTime(timezone=True), nullable=False),
        Column("message_count", Integer, nullable=False, default=0),
        Column("meta", JSON, nullable=True),
    )
    Table(
        "models",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(128), nullable=False, unique=True),
        Column("provider", String(64), nullable=False),
        Column("base_url", String(512), nullable=False),
        Column("model", String(128), nullable=False),
        Column("max_context_tokens", Integer, nullable=False),
        Column("enabled", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "tools",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(128), nullable=False, unique=True),
        Column("version", String(64), nullable=False),
        Column("description", Text, nullable=False),
        Column("params_schema", JSON, nullable=False),
        Column("enabled", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "tool_invocations",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("session_id", String(128), nullable=False),
        Column("trace_id", String(64), nullable=False),
        Column("tool_name", String(128), nullable=False),
        Column("ok", Boolean, nullable=False),
        Column("error_code", String(64), nullable=True),
        Column("duration_ms", Integer, nullable=False, default=0),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    Table(
        "request_metrics",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("trace_id", String(64), nullable=False),
        Column("session_id", String(128), nullable=False),
        Column("steps", Integer, nullable=False),
        Column("tool_calls", Integer, nullable=False),
        Column("prompt_tokens", Integer, nullable=False),
        Column("completion_tokens", Integer, nullable=False),
        Column("duration_ms", Integer, nullable=False, default=0),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    return metadata


def _degraded(operation: str) -> None:
    LOGGER.warning(
        "systemdb.degraded",
        extra={"event": "systemdb.degraded", "operation": operation},
    )
