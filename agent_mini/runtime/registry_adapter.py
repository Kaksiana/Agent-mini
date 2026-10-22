"""S06 ToolRegistry 到 S04 ToolExecutor 的适配器。"""

from agent_mini.llm.models import ToolCall, ToolSchema
from agent_mini.tools.registry import ToolRegistry, ToolResult


class RegistryExecutor:
    """把注册表适配为 Runtime 的 ToolExecutor Protocol。"""

    def __init__(self, registry: ToolRegistry) -> None:
        """保存注册表实例。"""
        self._registry = registry

    def schemas(self) -> list[ToolSchema]:
        """返回注册表当前的 OpenAI tools Schema。"""
        return [ToolSchema.model_validate(schema) for schema in self._registry.schemas()]

    async def execute(self, call: ToolCall) -> ToolResult:
        """执行一次 ToolCall；call 绑定由 Runtime 保持。"""
        return await self._registry.execute(call.name, call.arguments)
