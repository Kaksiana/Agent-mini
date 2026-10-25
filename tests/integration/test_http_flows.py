"""S18 回填：calculator、记忆、工具追问、双会话与并发。"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pytest

import agent_mini.tools.builtin as builtin
from agent_mini.context.builder import ContextBuilder
from agent_mini.context.token_counter import TokenCounter
from agent_mini.interface.http import create_app, create_app_from_env
from agent_mini.llm.models import LLMResponse, Message, ToolCall, Usage
from agent_mini.memory.base import StoredRound
from agent_mini.observability.errors import ConfigError
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = pytest.mark.integration
_ = builtin


class _Encoder:
    def encode(self, text: str) -> list[int]:
        return list(range(len(text)))


class _Short:
    def __init__(self) -> None:
        self.data: dict[str, list[StoredRound]] = {}

    async def append_round(
        self,
        session_id: str,
        messages: list[Message],
        round_id: str,
        truncated: bool = False,
        termination_reason: str | None = None,
    ) -> bool:
        self.data.setdefault(session_id, []).append(
            StoredRound(round_id, tuple(messages), truncated, termination_reason)
        )
        return True

    async def get_recent_rounds(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[StoredRound]:
        return list(self.data.get(session_id, []))


class _Scripted:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls: list[list[Message]] = []

    async def chat(
        self,
        messages: list[Message],
        tools: list[Any] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.calls.append(list(messages))
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


def _tool_call(call_id: str, name: str, arguments: dict[str, object]) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        finish_reason="tool_calls",
        usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _final(text: str) -> LLMResponse:
    return LLMResponse(
        content=text,
        finish_reason="stop",
        usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _agent(llm: object, short: _Short | None = None) -> Agent:
    agent = Agent(
        cast(Any, llm),
        tool_executor=RegistryExecutor(DEFAULT_REGISTRY),
        short_term=short,
    )
    return agent.with_context(ContextBuilder(TokenCounter(_Encoder()), 1_000_000))


def _client(app: object) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=cast(Any, app), raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_calculator_http() -> None:
    llm = _Scripted([_tool_call("c1", "calculator", {"expression": "2+2"}), _final("4")])
    app = create_app(_agent(llm), {})
    async with _client(app) as client:
        response = await client.post("/chat", json={"message": "2+2"})
    body = response.json()
    assert response.status_code == 200
    assert body["tool_calls"] == 1
    assert "4" in body["reply"]


async def test_two_turn_memory_http() -> None:
    short = _Short()
    llm = _Scripted([_final("你好 Alice"), _final("Alice")])
    app = create_app(_agent(llm, short), {})
    async with _client(app) as client:
        first = await client.post("/chat", json={"session_id": "A", "message": "我叫 Alice"})
        second = await client.post("/chat", json={"session_id": "A", "message": "我叫什么"})
    assert first.status_code == second.status_code == 200
    assert second.json()["reply"] == "Alice"
    assert any("Alice" in str(message.content) for message in llm.calls[1])
    assert first.json()["session_id"] == second.json()["session_id"] == "A"


async def test_fourteen_rounds_are_trimmed_http() -> None:
    short = _Short()
    short.data["A"] = [
        StoredRound(
            f"r{index}",
            (
                Message(role="user", content=f"old-{index}"),
                Message(role="assistant", content="ok"),
            ),
        )
        for index in range(14)
    ]
    llm = _Scripted([_final("ok")])
    app = create_app(_agent(llm, short), {})
    async with _client(app) as client:
        response = await client.post("/chat", json={"session_id": "A", "message": "new"})
    assert response.status_code == 200
    assert not any("old-0" in str(message.content) for message in llm.calls[0])


async def test_two_sessions_do_not_cross() -> None:
    short = _Short()
    llm = _Scripted([_final("A"), _final("B"), _final("A2"), _final("B2")])
    app = create_app(_agent(llm, short), {})
    async with _client(app) as client:
        await client.post("/chat", json={"session_id": "A", "message": "alpha"})
        await client.post("/chat", json={"session_id": "B", "message": "beta"})
        await client.post("/chat", json={"session_id": "A", "message": "alpha2"})
        await client.post("/chat", json={"session_id": "B", "message": "beta2"})
    assert len(short.data["A"]) == 2
    assert len(short.data["B"]) == 2


async def test_tool_follow_up_http() -> None:
    short = _Short()
    llm = _Scripted(
        [
            _tool_call("c1", "calculator", {"expression": "2+2"}),
            _final("4"),
            _tool_call("c2", "calculator", {"expression": "4*3"}),
            _final("12"),
        ]
    )
    app = create_app(_agent(llm, short), {})
    async with _client(app) as client:
        first = await client.post("/chat", json={"session_id": "A", "message": "2+2"})
        second = await client.post("/chat", json={"session_id": "A", "message": "再乘 3"})
    assert first.status_code == second.status_code == 200
    assert "4" in first.json()["reply"]
    assert "12" in second.json()["reply"]


async def test_concurrent_sessions() -> None:
    short = _Short()
    llm = _Scripted([_final("ok")])
    app = create_app(_agent(llm, short), {})
    async with _client(app) as client:
        responses = await asyncio.gather(
            *[
                client.post("/chat", json={"session_id": f"S{index}", "message": "hi"})
                for index in range(10)
            ]
        )
    assert all(response.status_code == 200 for response in responses)
    assert len(short.data) == 10


def test_env_factory_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="配置缺失"):
        create_app_from_env()


async def test_three_llm_tool_chain_http() -> None:
    llm = _Scripted(
        [
            _tool_call("c1", "calculator", {"expression": "2+2"}),
            _tool_call("c2", "todo", {"action": "add", "content": "4"}),
            _final("done"),
        ]
    )
    app = create_app(_agent(llm), {})
    async with _client(app) as client:
        response = await client.post("/chat", json={"session_id": "A", "message": "calc+todo"})
    assert response.status_code == 200
    assert len(llm.calls) == 3
    assert response.json()["tool_calls"] == 2
