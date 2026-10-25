"""TC-L4-001/003/007/008/012、TC-L3-008：HTTP 接口契约。"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pytest

from agent_mini.context.window import ContextTooLarge
from agent_mini.interface.http import create_app
from agent_mini.llm.errors import LLMError, LLMRateLimitError, LLMTimeoutError
from agent_mini.llm.models import Usage
from agent_mini.observability.errors import (
    ConfigError,
    InputError,
    SandboxError,
    SystemDBError,
    ToolError,
)
from agent_mini.runtime.result import AgentResult, ThoughtStep

pytestmark = pytest.mark.integration


class _Agent:
    def __init__(self, result: AgentResult | None = None) -> None:
        self.result = result or AgentResult(
            reply="你好",
            steps=1,
            usage=Usage(prompt_tokens=2, completion_tokens=3, total_tokens=5),
            trace=(ThoughtStep(step=1, decision="final", thought="回答"),),
            tool_calls=0,
            trace_id="trace-1",
        )
        self.calls: list[tuple[str, str, str]] = []

    async def run(
        self,
        user_input: str,
        session_id: str | None = None,
        trace_id: str | None = None,
    ) -> AgentResult:
        self.calls.append((user_input, session_id or "", trace_id or ""))
        return self.result.model_copy(update={"session_id": session_id, "trace_id": trace_id})


def _app(agent: object) -> Any:
    return create_app(cast(Any, agent), {"redis": lambda: True, "mongo": lambda: True})


async def _post(app: object, payload: dict[str, object]) -> httpx.Response:
    transport = httpx.ASGITransport(app=cast(Any, app), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/chat", json=payload)


async def test_chat_contract_and_generated_session() -> None:
    agent = _Agent()
    response = await _post(_app(agent), {"message": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "session_id",
        "reply",
        "steps",
        "tool_calls",
        "usage",
        "trace",
        "trace_id",
        "truncated",
    }
    assert body["reply"] == "你好"
    assert body["tool_calls"] == 0
    assert body["truncated"] is False
    assert body["usage"] == {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
    assert body["trace"][0]["decision"] == "final"
    assert len(body["session_id"]) >= 32
    assert len(body["trace_id"]) >= 16


async def test_existing_session_is_reused() -> None:
    agent = _Agent()
    response = await _post(_app(agent), {"session_id": "A", "message": "hi"})

    assert response.json()["session_id"] == "A"
    assert agent.calls[0][1] == "A"


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (LLMTimeoutError("timeout"), 408, "LLM_TIMEOUT"),
        (LLMRateLimitError("rate"), 429, "LLM_RATE_LIMITED"),
        (LLMError("bad"), 502, "LLM_ERROR"),
        (RuntimeError("boom"), 500, "INTERNAL"),
        (ContextTooLarge(), 400, "CONTEXT_TOO_LARGE"),
        (ConfigError("config"), 500, "CONFIG_ERROR"),
        (ToolError("tool"), 500, "TOOL_ERROR"),
        (SandboxError("sandbox"), 400, "SANDBOX_VIOLATION"),
        (InputError("input"), 400, "INVALID_INPUT"),
        (SystemDBError("db"), 500, "SYSTEMDB_ERROR"),
    ],
)
async def test_error_mapping(exc: Exception, status: int, code: str) -> None:
    class Broken:
        async def run(self, *args: object, **kwargs: object) -> AgentResult:
            raise exc

    response = await _post(_app(Broken()), {"message": "hi"})

    assert response.status_code == status
    assert response.json()["code"] == code
    assert "traceback" not in response.text.lower()
    assert "Traceback" not in response.text


async def test_invalid_request_is_400() -> None:
    response = await _post(_app(_Agent()), {"message": "   "})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_INPUT"


async def test_health_does_not_leak_secrets() -> None:
    app = create_app(
        cast(Any, _Agent()),
        {
            "redis": lambda: True,
            "mongo": lambda: False,
            "mysql": lambda: (_ for _ in ()).throw(RuntimeError("password=secret")),
        },
    )
    transport = httpx.ASGITransport(app=cast(Any, app), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded"
    assert body["dependencies"] == {
        "redis": "ok",
        "mongo": "unavailable",
        "mysql": "unavailable",
    }
    assert "secret" not in response.text
    assert "dsn" not in response.text.lower()


async def test_secret_values_are_redacted() -> None:
    secret = "sk-sentinel1234567890"
    agent = _Agent(
        AgentResult(
            reply=f"key={secret} Authorization: Bearer abc",
            steps=1,
            usage=Usage(),
            trace=(),
            trace_id="t",
        )
    )
    response = await _post(_app(agent), {"message": "hi"})

    assert secret not in response.text
    assert "Bearer abc" not in response.text


async def test_truncated_result_returns_200() -> None:
    result = AgentResult(
        reply="达到最大步数限制，已停止。",
        steps=2,
        usage=Usage(),
        trace=(),
        truncated=True,
        termination_reason="max_steps",
        trace_id="t",
    )
    response = await _post(_app(_Agent(result)), {"message": "hi"})

    assert response.status_code == 200
    assert response.json()["truncated"] is True


async def test_error_trace_id_matches_request() -> None:
    class Broken:
        def __init__(self) -> None:
            self.trace = ""

        async def run(self, *args: object, **kwargs: object) -> AgentResult:
            self.trace = str(kwargs.get("trace_id", ""))
            raise RuntimeError("boom")

    broken = Broken()
    response = await _post(_app(broken), {"message": "hi"})

    assert response.status_code == 500
    assert response.json()["trace_id"] == broken.trace


async def test_blank_session_is_400() -> None:
    response = await _post(_app(_Agent()), {"session_id": " ", "message": "hi"})
    assert response.status_code == 400


async def test_json_secret_is_redacted() -> None:
    secret = "sk-json1234567890"
    agent = _Agent(
        AgentResult(
            reply=f'{{"api_key": "{secret}", "Authorization": "Bearer abc"}}',
            steps=1,
            usage=Usage(),
            trace=(),
            trace_id="t",
        )
    )
    response = await _post(_app(agent), {"message": "hi"})

    assert secret not in response.text
    assert "Bearer abc" not in response.text


async def test_async_health_and_shutdown() -> None:
    class ClosableAgent(_Agent):
        def __init__(self) -> None:
            super().__init__()
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    async def ok() -> bool:
        await asyncio.sleep(0)
        return True

    agent = ClosableAgent()
    app = create_app(cast(Any, agent), {"redis": ok})
    transport = httpx.ASGITransport(app=cast(Any, app), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.json()["status"] == "ok"
    assert app.router.lifespan_context is not None


async def test_error_log_code_matches_response_and_level(caplog: Any) -> None:
    class Broken:
        async def run(self, *args: object, **kwargs: object) -> AgentResult:
            raise SandboxError("path_escape")

    with caplog.at_level("WARNING", logger="agent_mini"):
        response = await _post(_app(Broken()), {"message": "hi"})

    assert response.status_code == 400
    assert response.json()["code"] == "SANDBOX_VIOLATION"
    records = [item for item in caplog.records if getattr(item, "event", None) == "agent.error"]
    assert records
    assert getattr(records[-1], "code", None) == "SANDBOX_VIOLATION"
    assert records[-1].levelname == "WARNING"


async def test_context_too_large_keeps_evidence() -> None:
    error = ContextTooLarge(steps=2)
    error.trace = (ThoughtStep(step=1, decision="tool_call", thought="计算"),)

    class Broken:
        async def run(self, *args: object, **kwargs: object) -> AgentResult:
            raise error

    response = await _post(_app(Broken()), {"message": "hi"})
    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "CONTEXT_TOO_LARGE"
    assert body["steps"] == 2
    assert body["truncated"] is True
    assert body["trace"][0]["step"] == 1
    assert body["trace"][0]["thought"] == "计算"


async def test_unknown_error_hides_type_and_secret(caplog: Any) -> None:
    class Broken:
        async def run(self, *args: object, **kwargs: object) -> AgentResult:
            raise RuntimeError("sk-secret-value class-and-stack")

    with caplog.at_level("ERROR", logger="agent_mini"):
        response = await _post(_app(Broken()), {"message": "hi"})
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL"
    assert "RuntimeError" not in response.text
    assert "sk-secret" not in response.text
    assert any(item.levelname == "ERROR" for item in caplog.records)


async def test_health_empty_is_degraded() -> None:
    app = create_app(cast(Any, _Agent()), {})
    transport = httpx.ASGITransport(app=cast(Any, app))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


async def test_health_slow_check_times_out() -> None:
    async def slow() -> bool:
        await asyncio.sleep(10)
        return True

    app = create_app(cast(Any, _Agent()), {"slow": slow})
    transport = httpx.ASGITransport(app=cast(Any, app))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"]["slow"] == "unavailable"
