"""Agent Runtime 入口：直答、ReAct 工具循环与安全阀。"""

from uuid import uuid4

from agent_mini.llm.client import LLMClient
from agent_mini.llm.models import Message
from agent_mini.memory.base import ShortTermStore
from agent_mini.runtime.loop import LoopPolicy, ToolExecutor, run_react_loop
from agent_mini.runtime.result import AgentResult


class Agent:
    """通过构造器注入 LLM、工具、安全阀与短时记忆的 Runtime。"""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor | None = None,
        policy: LoopPolicy | None = None,
        short_term: ShortTermStore | None = None,
    ) -> None:
        """保存注入依赖；旧调用不传 short_term 时行为不变。"""
        self._llm_client = llm_client
        self._tool_executor = tool_executor
        self._policy = policy
        self._short_term = short_term

    async def run(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> AgentResult:
        """运行单轮；有 session_id 时在返回前同步写回。"""
        messages = [Message(role="user", content=user_input)]
        result = await run_react_loop(
            self._llm_client,
            messages,
            self._tool_executor,
            self._policy,
        )
        if session_id is not None and self._short_term is not None:
            await self._short_term.append_round(session_id, messages, uuid4().hex)
        if session_id is not None:
            result = result.model_copy(update={"session_id": session_id})
        return result
