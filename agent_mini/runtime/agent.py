"""Agent Runtime 入口：直答、ReAct 工具循环与安全阀。"""

from agent_mini.llm.client import LLMClient
from agent_mini.llm.models import Message
from agent_mini.runtime.loop import LoopPolicy, ToolExecutor, run_react_loop
from agent_mini.runtime.result import AgentResult


class Agent:
    """通过构造器注入 LLM、可选工具执行器与安全阀策略的 Runtime。"""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor | None = None,
        policy: LoopPolicy | None = None,
    ) -> None:
        """保存注入的模型客户端、工具执行器与循环策略。"""
        self._llm_client = llm_client
        self._tool_executor = tool_executor
        self._policy = policy

    async def run(self, user_input: str) -> AgentResult:
        """发送单条 user 消息并运行至最终文本。"""
        return await run_react_loop(
            self._llm_client,
            [Message(role="user", content=user_input)],
            self._tool_executor,
            self._policy,
        )
