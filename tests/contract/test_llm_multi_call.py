"""TC-L2-010：content 与多个 tool_calls 的解析边界。"""

import pytest

from agent_mini.llm.models import LLMResponse

pytestmark = pytest.mark.contract


def _tool_call(call_id: str, name: str) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": '{"value": 1}'},
    }


def test_content_and_multiple_tool_calls_are_preserved_in_order() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": "准备调用",
                    "tool_calls": [
                        _tool_call("call_1", "first"),
                        _tool_call("call_2", "second"),
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    response = LLMResponse.from_openai(payload)

    assert response.content == "准备调用"
    assert response.finish_reason == "tool_calls"
    assert [call.id for call in response.tool_calls] == ["call_1", "call_2"]
