"""OpenAI Chat Completions 异步客户端。"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any, NoReturn, Protocol

import httpx

from agent_mini.llm.errors import (
    LLMAuthError,
    LLMBadRequestError,
    LLMConnectionError,
    LLMError,
    LLMProtocolError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
)
from agent_mini.llm.models import LLMResponse, Message, ModelConfig, ToolSchema

_RESERVED_PARAMS = frozenset({"model", "thinking"})
_RETRYABLE_STATUS_CODES = frozenset({httpx.codes.TOO_MANY_REQUESTS})
_AUTH_STATUS_CODES = frozenset({httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN})
_SERVER_ERROR_MIN = httpx.codes.INTERNAL_SERVER_ERROR
_SERVER_ERROR_MAX_EXCLUSIVE = 600
_CLIENT_ERROR_MIN = 400
_CLIENT_ERROR_MAX_EXCLUSIVE = 500
MAX_ATTEMPTS_LIMIT = 3
DEFAULT_MAX_ATTEMPTS = MAX_ATTEMPTS_LIMIT
DEFAULT_BACKOFF_BASE_SECONDS = 0.5
DEFAULT_BACKOFF_FACTOR = 2
DEFAULT_JITTER_MAX_SECONDS = 0.1
DEFAULT_BACKOFF_MAX_SECONDS = 8.0

Sleep = Callable[[float], Awaitable[None]]
RetryEventSink = Callable[["RetryEvent"], None]


@dataclass(frozen=True)
class RetryEvent:
    """一次内部 HTTP 重试的可观察记录。"""

    attempt: int
    max_attempts: int
    status_code: int
    delay_seconds: float


@dataclass(frozen=True)
class RetryPolicy:
    """重试次数、等待函数与重试事件出口。"""

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    sleep: Sleep | None = None
    on_retry: RetryEventSink | None = None

    def __post_init__(self) -> None:
        """校验尝试次数和回调类型。"""
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("max_attempts 必须是整数")
        if not 1 <= self.max_attempts <= MAX_ATTEMPTS_LIMIT:
            raise ValueError(f"max_attempts 必须在 1–{MAX_ATTEMPTS_LIMIT} 之间")
        if self.sleep is not None and not callable(self.sleep):
            raise ValueError("sleep 必须是可调用对象")
        if self.on_retry is not None and not callable(self.on_retry):
            raise ValueError("on_retry 必须是可调用对象")


class LLMClient(Protocol):
    """模型客户端协议。"""

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        """发送单轮请求并返回归一化响应。"""
        ...


class HttpLLMClient:
    """基于 httpx 的 OpenAI 兼容客户端。"""

    def __init__(
        self,
        config: ModelConfig,
        api_key: str,
        thinking: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        """保存配置并创建异步 HTTP 客户端。"""
        if retry is not None and not isinstance(retry, RetryPolicy):
            raise TypeError("retry 必须是 RetryPolicy")
        policy = retry if retry is not None else RetryPolicy()
        self._config = config
        self._thinking = thinking
        self._max_attempts = policy.max_attempts
        self._sleep: Sleep = policy.sleep if policy.sleep is not None else _default_sleep
        self._on_retry = policy.on_retry
        self._retry_events: list[RetryEvent] = []
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=config.timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        """发送单轮请求；model/thinking 不可被额外参数覆盖。"""
        payload = self._build_payload(messages, tools, params)
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post("chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError(f"模型调用超时（{self._config.timeout} 秒）") from exc
            except httpx.RequestError as exc:
                raise LLMConnectionError("模型连接失败") from exc
            if response.is_success:
                return self._parse_response(response)
            if self._is_retryable(response.status_code):
                if attempt >= self._max_attempts:
                    self._raise_retry_exhausted(response.status_code)
                delay = self._backoff_delay(attempt)
                self._notify_retry(
                    RetryEvent(
                        attempt=attempt,
                        max_attempts=self._max_attempts,
                        status_code=response.status_code,
                        delay_seconds=delay,
                    )
                )
                await self._sleep(delay)
                continue
            raise self._client_error(response.status_code)
        raise LLMError("模型请求未完成")

    @property
    def retry_events(self) -> tuple[RetryEvent, ...]:
        """返回客户端已记录的重试事件快照。"""
        return tuple(self._retry_events)

    async def aclose(self) -> None:
        """关闭底层 HTTP 连接。"""
        await self._client.aclose()

    async def __aenter__(self) -> HttpLLMClient:
        """进入异步上下文。"""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """退出异步上下文并释放连接。"""
        await self.aclose()

    def _build_payload(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None,
        params: dict[str, object],
    ) -> dict[str, Any]:
        reserved = _RESERVED_PARAMS.intersection(params)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ValueError(f"不允许覆盖保留参数: {names}")
        if tools is not None and (
            not isinstance(tools, list) or not all(isinstance(tool, ToolSchema) for tool in tools)
        ):
            raise ValueError("tools 必须是 ToolSchema 列表")
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [message.to_provider(self._thinking) for message in messages],
            "thinking": {"type": "enabled" if self._thinking else "disabled"},
        }
        if tools:
            payload["tools"] = [tool.to_provider() for tool in tools]
        payload.update(params)
        return payload

    def _parse_response(self, response: httpx.Response) -> LLMResponse:
        try:
            body = response.json()
        except ValueError as exc:
            raise LLMProtocolError("响应不是合法 JSON") from exc
        return LLMResponse.from_openai(body)

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        is_server_error = _SERVER_ERROR_MIN <= status_code < _SERVER_ERROR_MAX_EXCLUSIVE
        return status_code in _RETRYABLE_STATUS_CODES or is_server_error

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        exponent = attempt - 1
        base: float = DEFAULT_BACKOFF_BASE_SECONDS * (DEFAULT_BACKOFF_FACTOR**exponent)
        bounded: float = min(base, DEFAULT_BACKOFF_MAX_SECONDS)
        jitter: float = float(random.uniform(0.0, DEFAULT_JITTER_MAX_SECONDS))
        return min(bounded + jitter, DEFAULT_BACKOFF_MAX_SECONDS)

    @staticmethod
    def _raise_retry_exhausted(status_code: int) -> NoReturn:
        if status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise LLMRateLimitError("模型限流，重试耗尽")
        raise LLMServerError("模型服务端错误，重试耗尽")

    def _notify_retry(self, event: RetryEvent) -> None:
        self._retry_events.append(event)
        if self._on_retry is not None:
            self._on_retry(event)

    @staticmethod
    def _client_error(status_code: int) -> LLMError:
        if status_code in _AUTH_STATUS_CODES:
            return LLMAuthError("模型鉴权失败")
        if _CLIENT_ERROR_MIN <= status_code < _CLIENT_ERROR_MAX_EXCLUSIVE:
            return LLMBadRequestError(f"模型请求失败（HTTP {status_code}）")
        return LLMProtocolError(f"模型返回不支持的状态（HTTP {status_code}）")


async def _default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)
