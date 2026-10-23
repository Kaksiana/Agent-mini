"""工具注册、Schema 生成与参数校验。"""

import asyncio
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

TOOL_ERROR_INVALID_ARGUMENTS = "invalid_arguments"
TOOL_ERROR_UNKNOWN_TOOL = "unknown_tool"
TOOL_ERROR_EXECUTION = "tool_execution_error"
TOOL_ERROR_DISABLED = "tool_disabled"
TOOL_ERROR_INVALID_RETURN = "invalid_tool_result"


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
        """校验 ok/error_code 与可读内容的一致性。"""
        if self.ok and self.error_code is not None:
            raise ValueError("成功结果不能携带 error_code")
        if not self.ok and not self.error_code:
            raise ValueError("失败结果必须携带 error_code")
        if not self.content.strip():
            raise ValueError("工具结果内容不能为空")


@dataclass(frozen=True)
class ToolSpec:
    """一个工具的注册信息。"""

    name: str
    description: str
    params_model: type[BaseModel]
    handler: Callable[..., Any]
    enabled_key: str | None = None

    def __post_init__(self) -> None:
        """注册前校验最小元数据。"""
        if not self.name.strip():
            raise ValueError("工具 name 不能为空")
        if not self.description.strip():
            raise ValueError("工具 description 不能为空")
        if not isinstance(self.params_model, type) or not issubclass(self.params_model, BaseModel):
            raise ValueError("params_model 必须是 BaseModel 子类")
        if not callable(self.handler):
            raise ValueError("handler 必须可调用")
        if self.enabled_key is not None and not self.enabled_key.strip():
            raise ValueError("enabled_key 不能为空字符串")

    def to_json_schema(self) -> dict[str, object]:
        """生成 OpenAI tools 中的函数结构。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params_model.model_json_schema(),
        }


class ToolRegistry:
    """工具注册表；不依赖 Runtime 或 LLM。"""

    def __init__(self, enabled: Mapping[str, bool] | None = None) -> None:
        """保存工具与启停配置；未配置的 enabled_key 默认启用。"""
        self._tools: dict[str, ToolSpec] = {}
        self._enabled = dict(enabled or {})

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
        """返回启用工具按注册顺序的公开 Schema。"""
        return [spec.to_json_schema() for spec in self._tools.values() if self._is_enabled(spec)]

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
        if not self._is_enabled(spec):
            return ToolResult(False, f"工具已禁用: {name}", TOOL_ERROR_DISABLED)
        invalid = _validate_arguments(spec, arguments)
        if invalid is not None:
            return invalid
        validated = spec.params_model.model_validate(arguments or {})
        try:
            raw = await _invoke(spec.handler, validated.model_dump(), context)
        except Exception:
            return ToolResult(False, "工具执行失败", TOOL_ERROR_EXECUTION)
        if not isinstance(raw, ToolResult):
            return ToolResult(False, "工具返回值不是 ToolResult", TOOL_ERROR_INVALID_RETURN)
        return raw

    def _is_enabled(self, spec: ToolSpec) -> bool:
        if spec.enabled_key is None:
            return True
        return self._enabled.get(spec.enabled_key, True)


def _validate_arguments(
    spec: ToolSpec,
    arguments: dict[str, object] | None,
) -> ToolResult | None:
    supplied = set(arguments or {})
    declared = set(spec.params_model.model_fields)
    if supplied - declared:
        return ToolResult(False, "工具参数包含未声明字段", TOOL_ERROR_INVALID_ARGUMENTS)
    try:
        spec.params_model.model_validate(arguments or {})
    except ValidationError as exc:
        return ToolResult(
            False,
            f"工具参数不合法: {exc.error_count()} 项",
            TOOL_ERROR_INVALID_ARGUMENTS,
        )
    return None


async def _invoke(
    handler: Callable[..., Any],
    arguments: dict[str, object],
    context: ToolContext | None,
) -> object:
    if "context" in inspect.signature(handler).parameters:
        arguments = {**arguments, "context": context}
    if inspect.iscoroutinefunction(handler):
        return await handler(**arguments)
    return await asyncio.to_thread(lambda: handler(**arguments))


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
