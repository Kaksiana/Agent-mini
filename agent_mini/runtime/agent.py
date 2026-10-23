"""Agent Runtime 入口：直答、ReAct 工具循环与安全阀。"""

import asyncio
import logging
from typing import cast
from uuid import uuid4

from agent_mini.llm.client import LLMClient
from agent_mini.llm.models import Message
from agent_mini.memory.base import ShortTermStore
from agent_mini.runtime.loop import LoopPolicy, ToolExecutor, run_react_loop
from agent_mini.runtime.result import AgentResult
from agent_mini.tools.registry import ToolContext

MEMORY_WRITEBACK_TIMEOUT_SECONDS = 5.0
LOGGER = logging.getLogger("agent_mini.runtime")


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
        """运行单轮；有 session_id 时在返回前同步写回 Redis。"""
        messages = [Message(role="user", content=user_input)]
        executor = self._executor_for(session_id)
        result = await run_react_loop(
            self._llm_client,
            messages,
            executor,
            self._policy,
        )
        if result.truncated:
            messages.append(Message(role="assistant", content=result.reply))
        if session_id is not None and self._short_term is not None:
            await self._write_back(session_id, messages, result)
        if session_id is not None:
            result = result.model_copy(update={"session_id": session_id})
        return result

    def _executor_for(self, session_id: str | None) -> ToolExecutor | None:
        if session_id is None or self._tool_executor is None:
            return self._tool_executor
        with_context = getattr(self._tool_executor, "with_context", None)
        if not callable(with_context):
            return self._tool_executor
        context = ToolContext(session_id=session_id, trace_id=uuid4().hex)
        return cast(ToolExecutor, with_context(context))

    async def _write_back(
        self,
        session_id: str,
        messages: list[Message],
        result: AgentResult,
    ) -> None:
        store = self._short_term
        if store is None:
            return
        try:
            await asyncio.wait_for(
                store.append_round(
                    session_id,
                    messages,
                    uuid4().hex,
                    result.truncated,
                    result.termination_reason,
                ),
                MEMORY_WRITEBACK_TIMEOUT_SECONDS,
            )
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )
