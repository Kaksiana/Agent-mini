"""S06 ToolRegistry 到 S04 ToolExecutor 的适配器。"""

from __future__ import annotations

from agent_mini.llm.models import ToolCall, ToolSchema
from agent_mini.tools.registry import ToolContext, ToolRegistry, ToolResult


class RegistryExecutor:
    """把注册表适配为 Runtime 的 ToolExecutor Protocol。"""

    def __init__(
        self,
        registry: ToolRegistry,
        context: ToolContext | None = None,
    ) -> None:
        """保存注册表与可选可信上下文。"""
        self._registry = registry
        self._context = context

    def with_context(self, context: ToolContext) -> RegistryExecutor:
        """返回带请求级可信上下文的新适配器。"""
        return RegistryExecutor(self._registry, context)

    def bind_request(self, session_id: str, trace_id: str) -> RegistryExecutor:
        """只替换请求级字段，保留 sandbox 配置。"""
        base = self._context
        context = ToolContext(
            session_id=session_id,
            trace_id=trace_id,
            sandbox_root=base.sandbox_root if base is not None else None,
            max_file_size=base.max_file_size if base is not None else None,
        )
        return RegistryExecutor(self._registry, context)

    def schemas(self) -> list[ToolSchema]:
        """返回注册表当前的 OpenAI tools Schema。"""
        return [ToolSchema.model_validate(schema) for schema in self._registry.schemas()]

    async def execute(self, call: ToolCall) -> ToolResult:
        """执行一次 ToolCall；call 绑定由 Runtime 保持。"""
        return await self._registry.execute(call.name, call.arguments, self._context)
