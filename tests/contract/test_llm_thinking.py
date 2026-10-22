"""TC-L2-007：reasoning 解析与 thinking 请求模式。"""

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import LLMResponse, Message, ModelConfig

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


@pytest.mark.parametrize("message", [{"content": "x"}, {"content": "x", "reasoning_content": None}])
def test_reasoning_missing_or_null_stays_none(message: dict[str, object]) -> None:
    payload = {"choices": [{"message": message, "finish_reason": "stop"}]}

    response = LLMResponse.from_openai(payload)

    assert response.content == "x"
    assert response.reasoning_content is None


def test_reasoning_is_parsed_independently() -> None:
    payload = {
        "choices": [
            {
                "message": {"content": "答案", "reasoning_content": "私有推理"},
                "finish_reason": "stop",
            }
        ]
    }

    response = LLMResponse.from_openai(payload)

    assert response.content == "答案"
    assert response.reasoning_content == "私有推理"


@pytest.mark.parametrize("role", ["user", "system", "tool"])
def test_reasoning_is_rejected_for_non_assistant(role: str) -> None:
    with pytest.raises(ValidationError):
        Message(role=role, content="内容", reasoning_content="私有推理")


def test_reasoning_is_allowed_for_assistant() -> None:
    message = Message(role="assistant", content="答案", reasoning_content="私有推理")

    assert message.reasoning_content == "私有推理"


async def test_default_mode_omits_reasoning_history() -> None:
    history = [
        Message(role="user", content="问题"),
        Message(role="assistant", content="答案", reasoning_content="私有推理"),
    ]
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json=_text_payload("ok"))
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            await client.chat(history)

    body = json.loads(route.calls[0].request.content)
    assert body["thinking"] == {"type": "disabled"}
    assert "reasoning_content" not in body["messages"][1]


async def test_enabled_mode_resends_reasoning_on_later_turn() -> None:
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            side_effect=[
                httpx.Response(200, json=_text_payload("第一轮")),
                httpx.Response(200, json=_text_payload("第二轮")),
            ]
        )
        async with HttpLLMClient(
            _config(),
            api_key=API_KEY,
            thinking=True,
        ) as client:
            messages = [Message(role="user", content="第一问")]
            await client.chat(messages)
            messages.append(
                Message(role="assistant", content="第一轮", reasoning_content="私有推理")
            )
            messages.append(Message(role="user", content="第二问"))
            await client.chat(messages)

    second_body = json.loads(route.calls[1].request.content)
    assert second_body["thinking"] == {"type": "enabled"}
    assert second_body["messages"][1]["reasoning_content"] == "私有推理"
