"""Agent Runtime 入口：直答、ReAct 工具循环与安全阀。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import cast
from uuid import uuid4

from agent_mini.context.builder import BuildRequest, ContextBuilder
from agent_mini.llm.client import LLMClient
from agent_mini.llm.models import Message, ToolSchema
from agent_mini.memory.base import (
    MidTermStore,
    ShortTermStore,
    StoredRound,
    valid_session_id,
)
from agent_mini.runtime.loop import LoopOptions, LoopPolicy, ToolExecutor, run_react_loop
from agent_mini.runtime.result import AgentResult
from agent_mini.tools.registry import ToolContext

MEMORY_WRITEBACK_TIMEOUT_SECONDS = 5.0
LOGGER = logging.getLogger("agent_mini.runtime")


class Agent:
    """通过构造器注入 LLM、工具、安全阀与记忆的 Runtime。"""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_executor: ToolExecutor | None = None,
        policy: LoopPolicy | None = None,
        short_term: ShortTermStore | None = None,
        memory_timeout: float = MEMORY_WRITEBACK_TIMEOUT_SECONDS,
    ) -> None:
        """保存注入依赖；旧调用不传记忆时行为不变。"""
        self._llm_client = llm_client
        self._tool_executor = tool_executor
        self._policy = policy
        self._short_term = short_term
        self._memory_timeout = memory_timeout
        self._mid_term: MidTermStore | None = None
        self._mongo_timeout = MEMORY_WRITEBACK_TIMEOUT_SECONDS
        self._context_builder: ContextBuilder | None = None
        self._system_prompt: str | None = None
        self._include_reasoning = True
        self._background: set[asyncio.Task[None]] = set()

    def with_context(
        self,
        builder: ContextBuilder,
        system_prompt: str | None = None,
        include_reasoning: bool = True,
    ) -> Agent:
        """启用 Context 组装与同一快照出站。"""
        self._context_builder = builder
        self._system_prompt = system_prompt
        self._include_reasoning = include_reasoning
        return self

    def with_mid_term(self, mid_term: MidTermStore, timeout: float) -> Agent:
        """启用响应后异步 Mongo 写回。"""
        self._mid_term = mid_term
        self._mongo_timeout = timeout
        return self

    async def drain(self) -> None:
        """限时等待所有后台 Mongo 写回完成。"""
        if not self._background:
            return
        tasks = tuple(self._background)
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                self._mongo_timeout,
            )
        except TimeoutError:
            LOGGER.warning(
                "memory.degraded",
                extra={
                    "event": "memory.degraded",
                    "operation": "drain",
                    "remaining": len(self._background),
                },
            )

    async def close(self) -> None:
        """关闭前排空后台写入。"""
        await self.drain()

    async def run(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> AgentResult:
        """运行单轮；响应前同步 Redis，响应后异步 Mongo。"""
        if session_id is not None and not valid_session_id(session_id):
            raise ValueError("session_id 非法")
        executor = self._executor_for(session_id)
        messages, tools_snapshot, context_fit = await self._build_context(
            user_input,
            session_id,
            executor,
        )
        result = await run_react_loop(
            self._llm_client,
            messages,
            executor,
            self._policy,
            LoopOptions(tools_snapshot, context_fit),
        )
        if result.truncated:
            messages.append(Message(role="assistant", content=result.reply))
        stored = StoredRound(
            uuid4().hex,
            tuple(messages),
            result.truncated,
            result.termination_reason,
        )
        if session_id is not None and self._short_term is not None:
            await self._write_back(session_id, stored)
        if session_id is not None and self._mid_term is not None:
            task = asyncio.create_task(self._write_mongo(session_id, stored))
            self._background.add(task)
            task.add_done_callback(self._background.discard)
        if session_id is not None:
            result = result.model_copy(update={"session_id": session_id})
        return result

    async def _build_context(
        self,
        user_input: str,
        session_id: str | None,
        executor: ToolExecutor | None,
    ) -> tuple[
        list[Message],
        tuple[ToolSchema, ...] | None,
        Callable[[list[Message]], Awaitable[list[Message]]] | None,
    ]:
        builder = self._context_builder
        if builder is None:
            return [Message(role="user", content=user_input)], None, None
        tools_snapshot = tuple(executor.schemas() if executor is not None else ())
        request = BuildRequest(
            user_input=user_input,
            tools_snapshot=tools_snapshot,
            session_id=session_id,
            short_term=self._short_term,
            mid_term=self._mid_term,
            system_prompt=self._system_prompt,
            include_reasoning=self._include_reasoning,
        )
        payload = await builder.build(request)

        async def fit(messages: list[Message]) -> list[Message]:
            updated = await builder.fit(request, messages)
            return list(updated.messages)

        return list(payload.messages), payload.tools_snapshot, fit

    def _executor_for(self, session_id: str | None) -> ToolExecutor | None:
        if session_id is None or self._tool_executor is None:
            return self._tool_executor
        bind_request = getattr(self._tool_executor, "bind_request", None)
        if callable(bind_request):
            return cast(ToolExecutor, bind_request(session_id, uuid4().hex))
        with_context = getattr(self._tool_executor, "with_context", None)
        if not callable(with_context):
            return self._tool_executor
        context = ToolContext(session_id=session_id, trace_id=uuid4().hex)
        return cast(ToolExecutor, with_context(context))

    async def _write_back(self, session_id: str, stored: StoredRound) -> None:
        store = self._short_term
        if store is None:
            return
        try:
            await asyncio.wait_for(
                store.append_round(
                    session_id,
                    list(stored.messages),
                    stored.round_id,
                    stored.truncated,
                    stored.termination_reason,
                ),
                self._memory_timeout,
            )
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )

    async def _write_mongo(self, session_id: str, stored: StoredRound) -> None:
        mid_term = self._mid_term
        if mid_term is None:
            return
        try:
            await asyncio.wait_for(
                mid_term.append_round(session_id, stored),
                self._mongo_timeout,
            )
        except Exception:
            LOGGER.warning(
                "memory.degraded",
                extra={"event": "memory.degraded", "session_id": session_id},
            )
