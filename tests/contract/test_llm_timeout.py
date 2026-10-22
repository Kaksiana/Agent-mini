"""TC-L2-005：超时不重试。"""

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


async def test_read_timeout_raises_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []

    def fake_sleep(delay: float) -> asyncio.Future[None]:
        delays.append(delay)
        future = asyncio.get_running_loop().create_future()
        future.set_result(None)
        return future

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=httpx.ReadTimeout("read timed out")
        )
        async with HttpLLMClient(
            ModelConfig(base_url=BASE_URL, model="deepseek-chat", timeout=5.0),
            api_key=API_KEY,
        ) as client:
            with pytest.raises(llm_errors.LLMError, match=r"5\.0") as exc_info:
                await client.chat([Message(role="user", content="hi")])

    assert route.call_count == 1
    assert delays == []
    assert exc_info.value.code == "LLM_TIMEOUT"
    assert type(exc_info.value).__name__ == "LLMTimeoutError"
