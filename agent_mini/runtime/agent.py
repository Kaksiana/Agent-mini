"""S03 单轮直答 Agent。"""

from agent_mini.llm.client import LLMClient
from agent_mini.llm.errors import LLMEmptyResponseError, LLMProtocolError
from agent_mini.llm.models import Message
from agent_mini.runtime.result import AgentResult

DIRECT_REPLY_STEPS = 1


class Agent:
    """通过构造器注入 LLM 的最小 Runtime。"""

    def __init__(self, llm_client: LLMClient) -> None:
        """保存注入的模型客户端。"""
        self._llm_client = llm_client

    async def run(self, user_input: str) -> AgentResult:
        """发送单条 user 消息并返回一步直答结果。"""
        response = await self._llm_client.chat([Message(role="user", content=user_input)])
        if response.tool_calls:
            raise LLMProtocolError("S03 不支持工具调用")
        if response.content is None or not response.content.strip():
            raise LLMEmptyResponseError("模型没有返回有效答案")
        return AgentResult(
            reply=response.content,
            steps=DIRECT_REPLY_STEPS,
            usage=response.usage,
        )
