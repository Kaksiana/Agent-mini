"""LLM 数据模型与响应归一。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal, NoReturn, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent_mini.llm.errors import (
    LLMEmptyResponseError,
    LLMOutputRejectedError,
    LLMOutputTruncatedError,
    LLMProtocolError,
)

_ALLOWED_FINISH_REASONS = {"stop", "tool_calls"}
_INVALID_ARGUMENTS = "invalid_arguments"


class ModelConfig(BaseModel):
    """S01 临时模型配置，待 S21 迁移到配置层。"""

    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    timeout: float = Field(default=60.0, gt=0)


class ToolCall(BaseModel):
    """归一化后的工具调用。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] | None = None
    raw_arguments: str | None = None
    error_code: str | None = None

    def to_provider(self) -> dict[str, Any]:
        """转换为供应商 tool_calls 元素。"""
        raw = self.raw_arguments
        if raw is None:
            raw = json.dumps(
                self.arguments or {},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": raw},
        }


class ToolSchema(BaseModel):
    """请求中使用的工具定义。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str
    parameters: dict[str, Any]

    def to_provider(self) -> dict[str, Any]:
        """转换为请求 tools 元素。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Usage(BaseModel):
    """Token 用量。"""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class Message(BaseModel):
    """一条 Chat Completions 消息。"""

    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    reasoning_content: str | None = None

    def to_provider(self, include_reasoning: bool) -> dict[str, Any]:
        """转换为供应商请求消息。"""
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        if self.tool_calls is not None:
            payload["tool_calls"] = [call.to_provider() for call in self.tool_calls]
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if include_reasoning and self.reasoning_content is not None:
            payload["reasoning_content"] = self.reasoning_content
        return payload


class LLMResponse(BaseModel):
    """归一化后的模型响应。"""

    content: str | None = None
    reasoning_content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    finish_reason: str

    @classmethod
    def from_openai(cls, payload: Mapping[str, Any]) -> LLMResponse:
        """校验并归一化上游响应。"""
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMProtocolError("响应缺少 choices")
        choice = _as_mapping(choices[0], "choice")
        finish_reason = choice.get("finish_reason")
        if not isinstance(finish_reason, str) or not finish_reason:
            raise LLMProtocolError("finish_reason 缺失")
        message = _as_mapping(choice.get("message"), "message")
        content = _optional_str(message.get("content"), "content")
        reasoning = _optional_str(message.get("reasoning_content"), "reasoning_content")
        tool_calls = _parse_tool_calls(message.get("tool_calls"))
        usage = _parse_usage(payload.get("usage"))
        if finish_reason == "length":
            raise LLMOutputTruncatedError("模型输出被截断")
        if finish_reason == "content_filter":
            raise LLMOutputRejectedError("模型输出被过滤")
        if finish_reason not in _ALLOWED_FINISH_REASONS:
            raise LLMProtocolError("未知的 finish_reason")
        if not tool_calls:
            if finish_reason == "tool_calls":
                raise LLMProtocolError("tool_calls 终止但没有调用")
            if content is None or not content.strip():
                raise LLMEmptyResponseError("模型没有返回有效答案")
        return cls(
            content=content,
            reasoning_content=reasoning,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
        )


def _as_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LLMProtocolError(f"{label} 结构不合法")
    return cast(Mapping[str, Any], value)


def _optional_str(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LLMProtocolError(f"{label} 类型不合法")
    return value


def _parse_usage(value: object | None) -> Usage:
    if value is None:
        return Usage()
    data = _as_mapping(value, "usage")
    try:
        return Usage(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )
    except ValidationError as exc:
        raise LLMProtocolError("usage 结构不合法") from exc


def _parse_tool_calls(value: object | None) -> list[ToolCall]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise LLMProtocolError("tool_calls 结构不合法")
    seen: set[str] = set()
    calls: list[ToolCall] = []
    for raw in value:
        item = _as_mapping(raw, "tool_call")
        call_id = item.get("id")
        if not isinstance(call_id, str) or not call_id:
            raise LLMProtocolError("tool_call id 为空")
        if call_id in seen:
            raise LLMProtocolError("tool_call id 重复")
        seen.add(call_id)
        if item.get("type") != "function":
            raise LLMProtocolError("tool_call 类型不合法")
        function = _as_mapping(item.get("function"), "function")
        name = function.get("name")
        raw_arguments = function.get("arguments")
        if not isinstance(name, str) or not name:
            raise LLMProtocolError("tool_call 名称不合法")
        if not isinstance(raw_arguments, str):
            raise LLMProtocolError("tool_call arguments 类型不合法")
        arguments, error_code = _parse_arguments(raw_arguments)
        calls.append(
            ToolCall(
                id=call_id,
                name=name,
                arguments=arguments,
                raw_arguments=raw_arguments,
                error_code=error_code,
            )
        )
    return calls


def _parse_arguments(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except ValueError:
        return None, _INVALID_ARGUMENTS
    if not isinstance(parsed, dict):
        return None, _INVALID_ARGUMENTS
    return cast(dict[str, Any], parsed), None


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"unsupported JSON constant: {value}")
