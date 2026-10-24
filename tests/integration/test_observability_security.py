"""TC-L5-004：假密钥/私有 reasoning 不进入 HTTP、日志与系统库。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from agent_mini.interface.http import create_app
from agent_mini.llm.models import LLMResponse, Message, ToolCall, ToolSchema, Usage
from agent_mini.runtime.agent import Agent
from agent_mini.systemdb.models import SystemDBConfig
from agent_mini.systemdb.repository import SystemDBRepository
from agent_mini.tools.registry import ToolResult

pytestmark = pytest.mark.integration


class _SecretLLM:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.calls = 0

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        **params: object,
    ) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call_secret",
                        name="leak",
                        arguments={"api_key": self.secret},
                    )
                ],
                finish_reason="tool_calls",
                usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        return LLMResponse(
            content=f"key={self.secret}",
            reasoning_content=f"private {self.secret}",
            finish_reason="stop",
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


class _SecretExecutor:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.calls = 0

    def schemas(self) -> list[ToolSchema]:
        return [ToolSchema(name="leak", description="leak", parameters={"type": "object"})]

    async def execute(self, call: ToolCall) -> ToolResult:
        self.calls += 1
        return ToolResult(True, f"tool result {self.secret}", None)


async def test_secret_and_reasoning_never_leave_memory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "sk-" + uuid4().hex
    llm = _SecretLLM(secret)
    executor = _SecretExecutor(secret)
    repo = SystemDBRepository(
        SystemDBConfig(dsn=f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}", auto_create=True)
    )
    assert await repo.ensure_schema()
    agent = Agent(cast(Any, llm), tool_executor=executor).with_system_db(repo, 1.0)
    app = create_app(agent)

    transport = httpx.ASGITransport(app=cast(Any, app), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with caplog.at_level("DEBUG", logger="agent_mini"):
            response = await client.post("/chat", json={"message": "leak"})
        await agent.drain()

    assert response.status_code == 200
    assert secret not in response.text
    assert "private" not in response.text
    assert executor.calls == 1

    async with repo.engine.connect() as connection:
        for table in ("sessions", "models", "tools", "tool_invocations", "request_metrics"):
            rows = await connection.execute(text(f"SELECT * FROM {table}"))
            assert secret not in str(rows.all())
    await repo.close()

    captured = capsys.readouterr()
    assert secret not in captured.err
    assert secret not in caplog.text
    assert "private" not in captured.err
