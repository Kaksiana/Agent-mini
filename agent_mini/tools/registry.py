"""工具注册、Schema 生成与参数校验。"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

TOOL_ERROR_INVALID_ARGUMENTS = "invalid_arguments"
TOOL_ERROR_UNKNOWN_TOOL = "unknown_tool"
TOOL_ERROR_EXECUTION = "tool_execution_error"


class ToolError(Exception):
    """工具层错误基类。"""


class ToolRegistrationError(ToolError):
    """工具注册失败。"""


class DuplicateToolError(ToolRegistrationError):
    """同名工具重复注册。"""


@dataclass(frozen=True)
class ToolContext:
    """S09 起使用的可信会话上下文；S06 只预留。"""

    session_id: str
    trace_id: str


@dataclass(frozen=True)
class ToolResult:
    """工具执行的唯一结果结构。"""

    ok: bool
    content: str
    error_code: str | None = None

    def __post_init__(self) -> None:
        """校验 ok 与 error_code 的一致性。"""
        if self.ok and self.error_code is not None:
            raise ValueError("成功结果不能携带 error_code")
        if not self.ok and not self.error_code:
            raise ValueError("失败结果必须携带 error_code")


@dataclass(frozen=True)
class ToolSpec:
    """一个工具的注册信息。"""

    name: str
    description: str
    params_model: type[BaseModel]
    handler: Callable[..., Any]
    enabled_key: str | None = None

    def to_json_schema(self) -> dict[str, object]:
        """生成 OpenAI tools 中的函数结构。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params_model.model_json_schema(),
        }


class ToolRegistry:
    """工具注册表；不依赖 Runtime 或 LLM。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """注册工具；同名必须拒绝，不覆盖原项。"""
        if spec.name in self._tools:
            raise DuplicateToolError(f"工具已注册: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        """按名称查找工具。"""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRegistrationError(f"工具不存在: {name}") from exc

    def schemas(self) -> list[dict[str, object]]:
        """返回注册顺序的公开 Schema。"""
        return [spec.to_json_schema() for spec in self._tools.values()]

    async def execute(
        self,
        name: str,
        arguments: dict[str, object] | None,
        context: ToolContext | None = None,
    ) -> ToolResult:
        """校验参数并执行；所有失败转为 ToolResult。"""
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(False, f"未知工具: {name}", TOOL_ERROR_UNKNOWN_TOOL)
        try:
            validated = spec.params_model.model_validate(arguments or {})
        except ValidationError as exc:
            return ToolResult(
                False,
                f"工具参数不合法: {exc.error_count()} 项",
                TOOL_ERROR_INVALID_ARGUMENTS,
            )
        try:
            raw = spec.handler(**validated.model_dump())
            if inspect.isawaitable(raw):
                raw = await raw
        except Exception:
            return ToolResult(False, "工具执行失败", TOOL_ERROR_EXECUTION)
        if isinstance(raw, ToolResult):
            return raw
        if isinstance(raw, str):
            return ToolResult(True, raw)
        return ToolResult(True, str(raw))


def tool(
    name: str,
    description: str,
    params_model: type[BaseModel],
    enabled_key: str | None = None,
    registry: ToolRegistry | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """注册装饰器；返回原 handler，便于直接测试。"""
    target = registry if registry is not None else DEFAULT_REGISTRY

    def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
        target.register(
            ToolSpec(
                name=name,
                description=description,
                params_model=params_model,
                handler=handler,
                enabled_key=enabled_key,
            )
        )
        return handler

    return decorator


DEFAULT_REGISTRY = ToolRegistry()
