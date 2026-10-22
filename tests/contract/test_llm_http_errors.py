"""TC-L2-006：4xx 不重试与错误分类。"""

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


@pytest.mark.parametrize(
    ("status", "error_name", "error_code"),
    [
        (400, "LLMBadRequestError", "LLM_BAD_REQUEST"),
        (401, "LLMAuthError", "LLM_AUTH"),
        (403, "LLMAuthError", "LLM_AUTH"),
    ],
)
async def test_4xx_is_not_retried(
    status: int,
    error_name: str,
    error_code: str,
    sleep_delays: list[float],
) -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(status))
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            with pytest.raises(llm_errors.LLMError) as exc_info:
                await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 1
    assert sleep_delays == []
    assert exc_info.value.code == error_code
    assert type(exc_info.value).__name__ == error_name


async def test_connection_error_is_not_retried(
    sleep_delays: list[float],
) -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=httpx.ConnectError("connection failed")
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            with pytest.raises(llm_errors.LLMError) as exc_info:
                await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 1
    assert sleep_delays == []
    assert exc_info.value.code == "LLM_CONNECTION_ERROR"
    assert type(exc_info.value).__name__ == "LLMConnectionError"
