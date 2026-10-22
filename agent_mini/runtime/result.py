"""S03 单轮直答结果模型。"""

from pydantic import BaseModel, ConfigDict

from agent_mini.llm.models import Usage


class AgentResult(BaseModel):
    """单轮直答的不可变结果。"""

    model_config = ConfigDict(frozen=True)

    reply: str
    steps: int
    usage: Usage
