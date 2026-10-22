"""S03 单轮直答结果模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_mini.llm.models import Usage


class AgentResult(BaseModel):
    """单轮直答的不可变结果。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reply: str = Field(min_length=1)
    steps: int = Field(ge=1)
    usage: Usage

    @field_validator("reply")
    @classmethod
    def _reply_must_not_be_blank(cls, value: str) -> str:
        """拒绝仅由空白组成的回复。"""
        if not value.strip():
            raise ValueError("reply 不能为纯空白")
        return value
