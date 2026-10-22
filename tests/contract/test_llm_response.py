"""TC-L2-002/003/010：响应归一与多工具调用解析。"""

import httpx
import pytest
import respx

from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import LLMResponse, Message, ModelConfig

pytestmark = pytest.mark.contract

BASE_URL = "https://api.example.com/v1"
API_KEY = "sk-test-not-a-real-key"


def _config() -> ModelConfig:
    return ModelConfig(base_url=BASE_URL, model="deepseek-chat", timeout=5.0)


def _tool_call(call_id: str, name: str, arguments: str) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


async def _chat(payload: dict[str, object]) -> LLMResponse:
    with respx.mock:
        respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json=payload)
        )
        async with HttpLLMClient(_config(), api_key=API_KEY) as client:
            return await client.chat([Message(role="user", content="hi")])


async def test_tool_call_response_is_normalized() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [_tool_call("call_1", "echo", '{"text": "hi"}')],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
    }
    response = await _chat(payload)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].id == "call_1"
    assert response.tool_calls[0].name == "echo"
    assert response.tool_calls[0].arguments == {"text": "hi"}
    assert response.finish_reason == "tool_calls"


async def test_text_response_preserves_content_and_usage() -> None:
    payload = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "你好"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
    }
    response = await _chat(payload)

    assert response.content == "你好"
    assert response.tool_calls == []
    assert response.usage.prompt_tokens == 4
    assert response.usage.completion_tokens == 2
    assert response.usage.total_tokens == 6


async def test_content_with_multiple_tool_calls_keeps_order() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "准备调用",
                    "tool_calls": [
                        _tool_call("call_1", "first", '{"value": 1}'),
                        _tool_call("call_2", "second", '{"value": 2}'),
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }
    response = await _chat(payload)

    assert response.content == "准备调用"
    assert [call.id for call in response.tool_calls] == ["call_1", "call_2"]
    assert response.finish_reason == "tool_calls"
