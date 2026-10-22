"""TC-L2-001：Chat Completions 请求契约。"""

import json

import httpx
import pytest
import respx

from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import Message, ModelConfig, ToolSchema

pytestmark = pytest.mark.contract

BASE_URL = "https://api.example.com/v1"
API_KEY = "sk-test-not-a-real-key"


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


async def test_chat_sends_openai_request_and_auth_header() -> None:
    tool = ToolSchema(
        name="echo",
        description="重复文本",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
    with respx.mock:
        route = respx.post(f"{BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(200, json=_text_payload("ok"))
        )
        async with HttpLLMClient(
            ModelConfig(base_url=BASE_URL, model="deepseek-chat", timeout=5.0),
            api_key=API_KEY,
        ) as client:
            response = await client.chat(
                [Message(role="user", content="hi")],
                tools=[tool],
            )

    request = route.calls[0].request
    body = json.loads(request.content)
    assert str(request.url) == f"{BASE_URL}/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert body["model"] == "deepseek-chat"
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    assert body["tools"][0]["function"]["name"] == "echo"
    assert body["tools"][0]["function"]["parameters"] == tool.parameters
    assert body["thinking"] == {"type": "disabled"}
    assert response.content == "ok"
