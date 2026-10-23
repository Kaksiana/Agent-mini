"""S17 系统数据库配置与记录模型。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agent_mini.runtime.result import AgentResult


@dataclass(frozen=True)
class SystemDBConfig:
    """系统数据库连接与初始化配置。"""

    dsn: str
    pool_size: int = 5
    pool_timeout_seconds: float = 2.0
    auto_create: bool = False


@dataclass(frozen=True)
class ModelRecord:
    """启动时登记的系统模型。"""

    name: str
    provider: str
    base_url: str
    model: str
    max_context_tokens: int
    enabled: bool = True


@dataclass(frozen=True)
class ToolRecord:
    """启动时登记的工具。"""

    name: str
    version: str
    description: str
    params_schema: dict[str, object]
    enabled: bool = True


@dataclass(frozen=True)
class ToolInvocationRecord:
    """一次工具调用审计。"""

    session_id: str
    trace_id: str
    tool_name: str
    ok: bool
    error_code: str | None
    duration_ms: int
    created_at: datetime


class SystemDBStore(Protocol):
    """Runtime 依赖的系统库最小接口。"""

    async def record_turn(
        self,
        session_id: str,
        result: AgentResult,
        duration_ms: int,
        trace_id: str,
    ) -> bool:
        """记录会话、工具审计与指标。"""
        ...


@dataclass(frozen=True)
class RequestMetricsRecord:
    """一次请求指标。"""

    trace_id: str
    session_id: str
    steps: int
    tool_calls: int
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int
    created_at: datetime
