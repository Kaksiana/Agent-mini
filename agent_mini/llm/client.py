"""OpenAI Chat Completions 异步客户端。"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol

import httpx

from agent_mini.llm.errors import LLMProtocolError
from agent_mini.llm.models import LLMResponse, Message, ModelConfig, ToolSchema

_RESERVED_PARAMS = frozenset({"model", "thinking"})


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
    ) -> None:
        """保存配置并创建异步 HTTP 客户端。"""
        self._config = config
        self._thinking = thinking
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
        response = await self._client.post("chat/completions", json=payload)
        response.raise_for_status()
        try:
            body = response.json()
        except ValueError as exc:
            raise LLMProtocolError("响应不是合法 JSON") from exc
        return LLMResponse.from_openai(body)

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
