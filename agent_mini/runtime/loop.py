"""S04 ReAct 工具循环。"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from agent_mini.llm.client import LLMClient
from agent_mini.llm.errors import LLMEmptyResponseError, LLMProtocolError
from agent_mini.llm.models import Message, ToolCall, ToolSchema, Usage
from agent_mini.runtime.result import (
    MAX_OBSERVATION_CHARS,
    AgentResult,
    ThoughtStep,
    ToolCallTrace,
)

_SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "access_key", "authorization", "password", "secret", "token"}
)
_SECRET_KEY_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|apikey|access[_-]?key|authorization|cookie|password|secret|token)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_SECRET_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_SK = re.compile(r"\bsk-[A-Za-z0-9_-]{4,}\b")


@dataclass(frozen=True)
class LoopPolicy:
    """S05 安全阀参数；默认不限制。"""

    max_steps: int | None = None
    deadline_seconds: float | None = None
    repeat_threshold: int | None = None
    clock: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class ToolOutcome:
    """S04 工具执行结果的最小结构。"""

    ok: bool
    content: str
    error_code: str | None = None


class ToolExecutor(Protocol):
    """S04 工具执行协议；S06 注册表负责适配。"""

    def schemas(self) -> list[ToolSchema]:
        """返回本轮冻结的工具 Schema。"""
        ...

    async def execute(self, call: ToolCall) -> ToolOutcome:
        """执行一次工具调用；实现方负责结构化错误。"""
        ...


async def run_react_loop(
    llm_client: LLMClient,
    messages: list[Message],
    tool_executor: ToolExecutor | None,
    policy: LoopPolicy | None = None,
) -> AgentResult:
    """运行至最终文本；S05 将通过 policy 接入步数/截止/重复检测。"""
    tools = tool_executor.schemas() if tool_executor is not None else None
    usage = Usage()
    trace: list[ThoughtStep] = []
    tool_traces: list[ToolCallTrace] = []
    tool_calls_count = 0
    step = 0
    while True:
        step += 1
        response = await llm_client.chat(messages, tools=tools)
        usage = _add_usage(usage, response.usage)
        reasoning_present = bool(response.reasoning_content)
        if response.tool_calls:
            if tool_executor is None:
                raise LLMProtocolError("未配置工具执行器，不能处理 tool_calls")
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                    reasoning_content=response.reasoning_content,
                )
            )
            step_traces: list[ToolCallTrace] = []
            for call in response.tool_calls:
                outcome = await _execute_call(tool_executor, call)
                messages.append(
                    Message(
                        role="tool",
                        content=outcome.content,
                        tool_call_id=call.id,
                    )
                )
                item = _tool_trace(call, outcome)
                step_traces.append(item)
                tool_traces.append(item)
                tool_calls_count += 1
            trace.append(
                ThoughtStep(
                    step=step,
                    decision="tool_call",
                    thought=_tool_thought(response.tool_calls),
                    reasoning_present=reasoning_present,
                    tool_calls=tuple(step_traces),
                )
            )
            continue
        if response.content is None or not response.content.strip():
            raise LLMEmptyResponseError("模型没有返回有效答案")
        messages.append(
            Message(
                role="assistant",
                content=response.content,
                reasoning_content=response.reasoning_content,
            )
        )
        trace.append(
            ThoughtStep(
                step=step,
                decision="final",
                thought="返回最终答案",
                reasoning_present=reasoning_present,
            )
        )
        return AgentResult(
            reply=response.content,
            steps=step,
            usage=usage,
            trace=tuple(trace),
            tool_calls=tool_calls_count,
            tool_traces=tuple(tool_traces),
        )


async def _execute_call(
    executor: ToolExecutor,
    call: ToolCall,
) -> ToolOutcome:
    if call.error_code is not None:
        return ToolOutcome(
            ok=False,
            content=f"工具参数不合法：{call.error_code}",
            error_code=call.error_code,
        )
    try:
        return await executor.execute(call)
    except Exception:
        return ToolOutcome(
            ok=False,
            content="工具执行失败",
            error_code="tool_execution_error",
        )


def _tool_trace(call: ToolCall, outcome: ToolOutcome) -> ToolCallTrace:
    secrets = _secret_values(call.arguments or {})
    observation = _sanitize_public_text(outcome.content, secrets)
    return ToolCallTrace(
        call_id=call.id,
        tool=call.name,
        args=_redact_args(call.arguments or {}),
        ok=outcome.ok,
        error_code=outcome.error_code,
        observation=observation[:MAX_OBSERVATION_CHARS],
    )


def _tool_thought(calls: list[ToolCall]) -> str:
    names = ", ".join(call.name for call in calls)
    return f"调用工具 {names}"


def _add_usage(total: Usage, item: Usage) -> Usage:
    return Usage(
        prompt_tokens=total.prompt_tokens + item.prompt_tokens,
        completion_tokens=total.completion_tokens + item.completion_tokens,
        total_tokens=total.total_tokens + item.total_tokens,
    )


def _redact_args(value: dict[str, object]) -> dict[str, object]:
    return {key: _redact_value(item, key) for key, item in value.items()}


def _redact_value(value: object, key: str | None = None) -> object:
    if key is not None and key.lower() in _SENSITIVE_KEYS:
        return "***"
    if isinstance(value, dict):
        return _redact_args(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _secret_values(value: object, key: str | None = None) -> set[str]:
    secrets: set[str] = set()
    if key is not None and key.lower() in _SENSITIVE_KEYS and isinstance(value, str):
        secrets.add(value)
    if isinstance(value, dict):
        for item_key, item in value.items():
            secrets.update(_secret_values(item, item_key))
    elif isinstance(value, list):
        for item in value:
            secrets.update(_secret_values(item))
    return secrets


def _sanitize_public_text(text: str, secrets: set[str]) -> str:
    """对公开 observation 做已知值、键值、Bearer 与 sk-* 脱敏。"""
    result = _SECRET_KEY_VALUE.sub(r"\1\2***", text)
    result = _SECRET_BEARER.sub("Bearer ***", result)
    result = _SECRET_SK.sub("***", result)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "***")
    return result
