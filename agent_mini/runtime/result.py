"""Agent Runtime 结果与可观察轨迹模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_mini.llm.models import Usage

MAX_OBSERVATION_CHARS = 200
ThoughtSource = Literal["runtime_summary"]


class ToolCallTrace(BaseModel):
    """公开的工具调用轨迹；不包含原始 reasoning。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    args: dict[str, object] = Field(default_factory=dict)
    ok: bool
    error_code: str | None = None
    observation: str

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

    @field_validator("reply")
    @classmethod
    def _reply_must_not_be_blank(cls, value: str) -> str:
        """拒绝仅由空白组成的回复。"""
        if not value.strip():
            raise ValueError("reply 不能为纯空白")
        return value
