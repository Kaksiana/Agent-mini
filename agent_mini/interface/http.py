"""S18 FastAPI 对外接口。"""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from agent_mini.context.window import ContextTooLarge
from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import ModelConfig
from agent_mini.observability.errors import AgentError, to_error_response
from agent_mini.observability.logging import (
    configure_logging,
    redact_text,
    reset_trace_context,
    set_trace_context,
)
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.runtime.result import AgentResult
from agent_mini.tools import builtin as _builtin
from agent_mini.tools.registry import DEFAULT_REGISTRY

MAX_MESSAGE_CHARS = 32_000
LOGGER = __import__("logging").getLogger("agent_mini.http")
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_SECONDS = 60.0
_ = _builtin


class ChatRequest(BaseModel):
    """POST /chat 请求。"""

    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)

    @field_validator("session_id")
    @classmethod
    def _session_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("session_id 不能为空白")
        return value

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message 不能为空白")
        return value


class UsageResponse(BaseModel):
    """usage 响应。"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """POST /chat 响应，字段与 DESIGN §3.6 一致。"""

    session_id: str
    reply: str
    steps: int
    tool_calls: int
    usage: UsageResponse
    trace: list[dict[str, object]]
    trace_id: str
    truncated: bool


def create_app_from_env() -> FastAPI:
    """从环境构造可运行应用；缺 Key 启动失败。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    config = ModelConfig(
        base_url=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        model=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        timeout=float(os.environ.get("DEEPSEEK_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)),
    )
    agent = Agent(
        HttpLLMClient(config, api_key),
        tool_executor=RegistryExecutor(DEFAULT_REGISTRY),
    )
    return create_app(agent)


def create_app(
    agent: Agent,
    health_checks: dict[str, Callable[[], bool | Awaitable[bool]]] | None = None,
) -> FastAPI:
    """创建无状态 FastAPI 应用。"""
    configure_logging()
    checks = health_checks or {}
    close = getattr(agent, "close", None)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            if callable(close):
                await close()

    app = FastAPI(title="agent-mini", lifespan=lifespan)
    app.state.health_checks = checks

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        started = monotonic()
        trace_id = uuid4().hex
        request.state.trace_id = trace_id
        request.state.session_id = payload.session_id or str(uuid4())
        request.state.started = started
        session_id = request.state.session_id
        set_trace_context(trace_id, session_id)
        try:
            result = await agent.run(
                payload.message,
                session_id=session_id,
                trace_id=trace_id,
            )
            LOGGER.info(
                "http.chat",
                extra={
                    "event": "http.chat",
                    "step": result.steps,
                    "tool_calls": result.tool_calls,
                    "prompt_tokens": result.usage.prompt_tokens,
                    "completion_tokens": result.usage.completion_tokens,
                    "total_tokens": result.usage.total_tokens,
                    "duration_ms": int((monotonic() - started) * 1000),
                },
            )
            return _to_response(result, session_id, trace_id)
        finally:
            reset_trace_context()

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        dependencies: dict[str, str] = {}
        healthy = True
        for name, check in checks.items():
            try:
                value = check()
                if inspect.isawaitable(value):
                    value = await value
                dependencies[name] = "ok" if value else "unavailable"
            except Exception:
                dependencies[name] = "unavailable"
            healthy = healthy and dependencies[name] == "ok"
        return {
            "status": "ok" if healthy else "degraded",
            "dependencies": dependencies,
        }

    @app.exception_handler(RequestValidationError)
    def validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", None) or uuid4().hex
        request.state.trace_id = trace_id
        LOGGER.warning(
            "http.validation_error",
            extra={
                "event": "http.validation_error",
                "code": "INVALID_INPUT",
                "trace_id": trace_id,
                "session_id": getattr(request.state, "session_id", None),
                "duration_ms": _elapsed_ms(request),
            },
        )
        return _error("INVALID_INPUT", "请求参数不合法", 400, request)

    @app.exception_handler(AgentError)
    def agent_error(request: Request, exc: AgentError) -> JSONResponse:
        level = logging.WARNING if exc.http_status < 500 else logging.ERROR
        LOGGER.log(
            level,
            "agent.error",
            extra={
                "event": "agent.error",
                "code": exc.code,
                "error_type": type(exc).__name__,
                "error_message": redact_text(str(exc)),
                "trace_id": getattr(request.state, "trace_id", None),
                "session_id": getattr(request.state, "session_id", None),
                "duration_ms": _elapsed_ms(request),
            },
        )
        message = "请求失败" if exc.http_status >= 500 else exc.message
        extra: dict[str, object] = {}
        if isinstance(exc, ContextTooLarge):
            extra = {
                "steps": exc.steps,
                "trace": list(exc.trace),
                "truncated": exc.truncated,
            }
        return _error(exc.code, message, exc.http_status, request, extra)

    @app.exception_handler(Exception)
    def internal_error(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.error(
            "http.error",
            exc_info=exc,
            extra={
                "event": "http.error",
                "code": "INTERNAL",
                "error_type": type(exc).__name__,
                "trace_id": getattr(request.state, "trace_id", None),
                "session_id": getattr(request.state, "session_id", None),
                "duration_ms": _elapsed_ms(request),
            },
        )
        return _error("INTERNAL", "内部错误", 500, request)

    return app


def _to_response(result: AgentResult, session_id: str, trace_id: str) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        reply=redact_text(result.reply),
        steps=result.steps,
        tool_calls=result.tool_calls,
        usage=UsageResponse(
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
            total_tokens=result.usage.total_tokens,
        ),
        trace=[
            item.model_dump(mode="json", exclude={"reasoning_content"}) for item in result.trace
        ],
        trace_id=result.trace_id or trace_id,
        truncated=result.truncated,
    )


def _elapsed_ms(request: Request) -> int:
    """请求已耗时，缺失起点时返回 0。"""
    started = getattr(request.state, "started", None)
    return int((monotonic() - started) * 1000) if started else 0


def _error(
    code: str,
    message: str,
    status: int,
    request: Request | None = None,
    extra: dict[str, object] | None = None,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None) if request is not None else None
    error = AgentError(message)
    error.code = code
    content = to_error_response(error, trace_id or uuid4().hex)
    content["message"] = redact_text(message)
    if extra:
        content.update(extra)
    return JSONResponse(status_code=status, content=content)
