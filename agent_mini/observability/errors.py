"""S20 统一异常层级与错误码。"""

from __future__ import annotations


class AgentError(Exception):
    """所有 Agent 业务异常的根。"""

    code: str = "AGENT_ERROR"
    http_status: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigError(AgentError):
    """配置缺失或非法。"""

    code = "CONFIG_ERROR"
    http_status = 500


class LLMError(AgentError):
    """模型调用与协议异常根。"""

    code = "LLM_ERROR"
    http_status = 502


class ToolError(AgentError):
    """工具注册或执行异常根。"""

    code = "TOOL_ERROR"
    http_status = 500


class SandboxError(AgentError):
    """沙箱路径/权限异常根。"""

    code = "SANDBOX_VIOLATION"
    http_status = 400


class ContextError(AgentError):
    """上下文预算/裁剪异常根。"""

    code = "CONTEXT_ERROR"
    http_status = 400


class InputError(AgentError):
    """请求入参异常。"""

    code = "INVALID_INPUT"
    http_status = 400


class SystemDBError(AgentError):
    """系统数据库异常根。"""

    code = "SYSTEMDB_ERROR"
    http_status = 500


ERROR_TYPES: tuple[type[AgentError], ...] = (
    ConfigError,
    LLMError,
    ToolError,
    SandboxError,
    ContextError,
    InputError,
    SystemDBError,
)


def to_error_response(error: AgentError, trace_id: str) -> dict[str, object]:
    """构造稳定错误响应体。"""
    return {
        "code": error.code,
        "message": error.message,
        "trace_id": trace_id,
    }
