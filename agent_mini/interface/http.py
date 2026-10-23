"""S18 FastAPI 对外接口。"""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from agent_mini.context.window import ContextTooLarge
from agent_mini.llm.errors import LLMError, LLMRateLimitError, LLMTimeoutError
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.result import AgentResult

MAX_MESSAGE_CHARS = 32_000
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(authorization|api[_-]?key|password|cookie)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{4,}\b"),
)


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


def create_app(
    agent: Agent,
    health_checks: dict[str, Callable[[], bool | Awaitable[bool]]] | None = None,
) -> FastAPI:
    """创建无状态 FastAPI 应用。"""
    app = FastAPI(title="agent-mini")
    checks = health_checks or {}
    app.state.health_checks = checks
    close = getattr(agent, "close", None)
    if callable(close):
        app.add_event_handler("shutdown", close)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        trace_id = uuid4().hex
        request.state.trace_id = trace_id
        session_id = payload.session_id or str(uuid4())
        result = await agent.run(
            payload.message,
            session_id=session_id,
            trace_id=trace_id,
        )
        return _to_response(result, session_id, trace_id)

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
        return _error("INVALID_REQUEST", "请求参数不合法", 400, request)

    @app.exception_handler(ContextTooLarge)
    def context_too_large(
        request: Request,
        exc: ContextTooLarge,
    ) -> JSONResponse:
        return _error("CONTEXT_TOO_LARGE", "上下文超过预算", 400, request)

    @app.exception_handler(LLMTimeoutError)
    def llm_timeout(
        request: Request,
        exc: LLMTimeoutError,
    ) -> JSONResponse:
        return _error("LLM_TIMEOUT", "模型调用超时", 408, request)

    @app.exception_handler(LLMRateLimitError)
    def llm_rate_limit(
        request: Request,
        exc: LLMRateLimitError,
    ) -> JSONResponse:
        return _error("LLM_RATE_LIMITED", "模型限流", 429, request)

    @app.exception_handler(LLMError)
    def llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return _error(exc.code, "模型不可用", 502, request)

    @app.exception_handler(Exception)
    def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return _error("INTERNAL_ERROR", "内部错误", 500, request)

    return app


def _to_response(result: AgentResult, session_id: str, trace_id: str) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        reply=_redact(result.reply),
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


def _error(
    code: str,
    message: str,
    status: int,
    request: Request | None = None,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None) if request is not None else None
    return JSONResponse(
        status_code=status,
        content={
            "code": code,
            "message": _redact(message),
            "trace_id": trace_id or uuid4().hex,
        },
    )


def _redact(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("***", result)
    return result
