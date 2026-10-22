"""TC-L2-008：响应判别与错误映射。"""

import pytest

from agent_mini.llm.errors import (
    LLMEmptyResponseError,
    LLMOutputRejectedError,
    LLMOutputTruncatedError,
    LLMProtocolError,
)
from agent_mini.llm.models import LLMResponse

pytestmark = pytest.mark.contract


def _tool_call(call_id: str, name: str = "echo") -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": "{}"},
    }


INVALID_PAYLOADS = [
    pytest.param({}, id="no-choices"),
    pytest.param({"choices": []}, id="empty-choices"),
    pytest.param(
        {"choices": [{"message": "bad", "finish_reason": "stop"}]},
        id="invalid-message",
    ),
    pytest.param(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [_tool_call("dup"), _tool_call("dup")],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        id="duplicate-call-id",
    ),
    pytest.param(
        {
            "choices": [
                {
                    "message": {"content": None, "tool_calls": [_tool_call("")]},
                    "finish_reason": "tool_calls",
                }
            ]
        },
        id="empty-call-id",
    ),
    pytest.param(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"arguments": "{}"},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        id="invalid-call-structure",
    ),
    pytest.param(
        {
            "choices": [
                {
                    "message": {"content": None, "tool_calls": []},
                    "finish_reason": "tool_calls",
                }
            ]
        },
        id="tool-calls-without-calls",
    ),
    pytest.param(
        {
            "choices": [
                {
                    "message": {"content": "answer"},
                    "finish_reason": "unknown_reason",
                }
            ]
        },
        id="unknown-finish-reason",
    ),
]


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_response_raises_protocol_error(payload: dict[str, object]) -> None:
    with pytest.raises(LLMProtocolError):
        LLMResponse.from_openai(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
            id="blank-content",
        ),
        pytest.param(
            {
                "choices": [
                    {
                        "message": {"content": None, "reasoning_content": "only"},
                        "finish_reason": "stop",
                    }
                ]
            },
            id="reasoning-only",
        ),
    ],
)
def test_no_valid_answer_raises_empty_response(payload: dict[str, object]) -> None:
    with pytest.raises(LLMEmptyResponseError):
        LLMResponse.from_openai(payload)


def test_length_raises_truncated() -> None:
    payload = {"choices": [{"message": {"content": "cut"}, "finish_reason": "length"}]}

    with pytest.raises(LLMOutputTruncatedError):
        LLMResponse.from_openai(payload)


def test_content_filter_raises_rejected() -> None:
    payload = {"choices": [{"message": {"content": "x"}, "finish_reason": "content_filter"}]}

    with pytest.raises(LLMOutputRejectedError):
        LLMResponse.from_openai(payload)
