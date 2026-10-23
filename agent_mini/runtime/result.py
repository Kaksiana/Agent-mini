"""Agent Runtime 结果与可观察轨迹模型。"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from agent_mini.llm.models import Usage

MAX_OBSERVATION_CHARS = 200
ThoughtSource = Literal["runtime_summary"]


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _to_plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    return value


class ToolCallTrace(BaseModel):
    """公开的工具调用轨迹；不包含原始 reasoning。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    args: dict[str, object] = Field(default_factory=dict)
    ok: bool
    error_code: str | None = None
    observation: str

    def model_post_init(self, __context: object) -> None:
        """把参数递归替换为只读映射/元组。"""
        object.__setattr__(self, "args", _freeze(self.args))

    @field_serializer("args")
    def _serialize_args(self, value: Mapping[str, object]) -> dict[str, object]:
        """序列化时恢复普通 JSON 结构，实例本身保持只读。"""
        return cast(dict[str, object], _to_plain(value))

    @field_validator("observation")
    @classmethod
    def _clip_observation(cls, value: str) -> str:
        """公开 observation 最多保留 200 字符。"""
        return value[:MAX_OBSERVATION_CHARS]


class ThoughtStep(BaseModel):
    """一次 LLM 响应对应的公开决策摘要。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step: int = Field(ge=1)
    decision: Literal["tool_call", "final", "error"]
    thought: str = Field(min_length=1)
    thought_source: ThoughtSource = "runtime_summary"
    reasoning_present: bool = False
    tool_calls: tuple[ToolCallTrace, ...] = ()
    error_code: str | None = None


class AgentResult(BaseModel):
    """单轮 Agent 的不可变结果。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reply: str = Field(min_length=1)
    steps: int = Field(ge=1)
    usage: Usage
    trace: tuple[ThoughtStep, ...] = ()
    tool_calls: int = Field(default=0, ge=0)
    tool_traces: tuple[ToolCallTrace, ...] = ()
    truncated: bool = False
    termination_reason: Literal["max_steps", "deadline", "repeat"] | None = None
    session_id: str | None = None

    @model_validator(mode="after")
    def _truncation_is_consistent(self) -> AgentResult:
        """truncated 与终止原因必须同时存在/同时为空。"""
        if self.truncated != (self.termination_reason is not None):
            raise ValueError("truncated 与 termination_reason 必须一致")
        return self

    @field_validator("reply")
    @classmethod
    def _reply_must_not_be_blank(cls, value: str) -> str:
        """拒绝仅由空白组成的回复。"""
        if not value.strip():
            raise ValueError("reply 不能为纯空白")
        return value
