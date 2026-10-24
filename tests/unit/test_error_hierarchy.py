"""TC-L1-019 / TC-L4-007：统一 AgentError 层级。"""

from __future__ import annotations

import pytest

from agent_mini.context.window import ContextTooLarge
from agent_mini.llm.errors import LLMError, LLMTimeoutError
from agent_mini.observability.errors import (
    ERROR_TYPES,
    AgentError,
    ConfigError,
    ContextError,
    InputError,
    SandboxError,
    SystemDBError,
    ToolError,
)
from agent_mini.tools.registry import ToolError as RegistryToolError
from agent_mini.tools.sandbox import SandboxViolation

pytestmark = pytest.mark.unit


def test_all_errors_are_agent_errors_and_codes_unique() -> None:
    classes = [*ERROR_TYPES, ContextTooLarge, LLMTimeoutError, RegistryToolError]
    assert all(issubclass(cls, AgentError) for cls in classes)
    assert issubclass(LLMError, AgentError)
    codes = [cls.code for cls in ERROR_TYPES]
    assert len(codes) == len(set(codes))


def test_context_and_sandbox_status() -> None:
    assert ContextTooLarge().http_status == 400
    assert ContextTooLarge().code == "CONTEXT_TOO_LARGE"
    violation = SandboxViolation("path_escape", "escape")
    assert violation.http_status == 400
    assert violation.code == "SANDBOX_VIOLATION"


def test_llm_and_tool_roots_are_shared() -> None:
    from agent_mini.llm.errors import LLMError as LlmRoot
    from agent_mini.observability.errors import LLMError as ObsLlmRoot
    from agent_mini.observability.errors import ToolError as ObsToolRoot
    from agent_mini.tools.registry import ToolError as RegistryToolRoot

    assert LlmRoot is ObsLlmRoot
    assert RegistryToolRoot is ObsToolRoot
    assert issubclass(LlmRoot, AgentError)
    assert issubclass(RegistryToolRoot, AgentError)


def test_required_error_subclasses() -> None:
    for cls in (
        ConfigError,
        LLMError,
        ToolError,
        SandboxError,
        ContextError,
        InputError,
        SystemDBError,
    ):
        assert issubclass(cls, AgentError)
