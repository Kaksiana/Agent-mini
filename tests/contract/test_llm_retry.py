"""TC-L2-004：429/5xx 退避重试。"""

import asyncio

import httpx
import pytest
import respx

from agent_mini.llm import errors as llm_errors
from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import Message, ModelConfig

pytestmark = pytest.mark.contract

BASE_URL = "https://api.example.com/v1"
API_KEY = "sk-test-not-a-real-key"


def _config() -> ModelConfig:
    return ModelConfig(base_url=BASE_URL, model="deepseek-chat", timeout=5.0)


def _text_payload(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


@pytest.fixture
def sleep_delays(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []

    def fake_sleep(delay: float) -> asyncio.Future[None]:
        delays.append(delay)
        future = asyncio.get_running_loop().create_future()
        future.set_result(None)
        return future

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return delays


async def test_retries_429_and_500_then_succeeds(sleep_delays: list[float]) -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(500),
                httpx.Response(200, json=_text_payload("ok")),
            ]
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            response = await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 3
    assert response.content == "ok"
    assert len(sleep_delays) == 2
    assert 0.5 <= sleep_delays[0] <= 0.6
    assert 1.0 <= sleep_delays[1] <= 1.1
    assert sleep_delays[0] < sleep_delays[1]


async def test_retry_exhaustion_returns_server_error(sleep_delays: list[float]) -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=[httpx.Response(500) for _ in range(3)]
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            with pytest.raises(llm_errors.LLMError) as exc_info:
                await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 3
    assert len(sleep_delays) == 2
    assert exc_info.value.code == "LLM_SERVER_ERROR"
    assert type(exc_info.value).__name__ == "LLMServerError"


async def test_retry_exhaustion_returns_rate_limit_error(sleep_delays: list[float]) -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=[httpx.Response(429) for _ in range(3)]
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            with pytest.raises(llm_errors.LLMError) as exc_info:
                await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 3
    assert len(sleep_delays) == 2
    assert exc_info.value.code == "LLM_RATE_LIMITED"
    assert type(exc_info.value).__name__ == "LLMRateLimitError"
