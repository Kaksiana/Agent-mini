"""TC-L2-009：工具参数严格 JSON 解析。"""

import pytest

from agent_mini.llm.models import LLMResponse

pytestmark = pytest.mark.contract


def _payload(arguments: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "echo", "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param('{"text": "hi"', id="broken-json"),
        pytest.param("[1, 2]", id="array-top-level"),
        pytest.param('"text"', id="string-top-level"),
        pytest.param('{"a": 1, "a": 2}', id="duplicate-key"),
        pytest.param('{"value": NaN}', id="nan"),
    ],
)
def test_invalid_arguments_keep_call_id_and_error(arguments: str) -> None:
    response = LLMResponse.from_openai(_payload(arguments))

    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.id == "call_1"
    assert call.arguments is None
    assert call.error_code == "invalid_arguments"


def test_valid_object_arguments_are_parsed() -> None:
    response = LLMResponse.from_openai(_payload('{"text": "hi"}'))

    call = response.tool_calls[0]
    assert call.arguments == {"text": "hi"}
    assert call.error_code is None


def test_invalid_arguments_can_be_followed_by_valid_response() -> None:
    invalid = LLMResponse.from_openai(_payload('{"text": "hi"'))
    valid = LLMResponse.from_openai(_payload('{"text": "hi"}'))

    assert invalid.tool_calls[0].error_code == "invalid_arguments"
    assert valid.tool_calls[0].arguments == {"text": "hi"}
