"""ReAct 工具循环与 S05 安全阀。"""

import asyncio
import json
import math
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from agent_mini.llm.client import LLMClient
from agent_mini.llm.errors import LLMEmptyResponseError, LLMProtocolError
from agent_mini.llm.models import LLMResponse, Message, ToolCall, ToolSchema, Usage
from agent_mini.runtime.result import (
    MAX_OBSERVATION_CHARS,
    AgentResult,
    ThoughtStep,
    ToolCallTrace,
)
from agent_mini.tools.registry import ToolResult

DEFAULT_MAX_STEPS = 8
DEFAULT_DEADLINE_SECONDS = 120.0
DEFAULT_REPEAT_THRESHOLD = 3
MAX_STEPS_MESSAGE = "已达到最大步数限制，已停止。"
DEADLINE_MESSAGE = "已达到截止时间限制，已停止。"
REPEAT_MESSAGE = "检测到重复工具调用，已停止。"
TerminationReason = Literal["max_steps", "deadline", "repeat"]
_SAFETY_MESSAGES: dict[TerminationReason, str] = {
    "max_steps": MAX_STEPS_MESSAGE,
    "deadline": DEADLINE_MESSAGE,
    "repeat": REPEAT_MESSAGE,
}
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
    """S05 安全阀参数。"""

    max_steps: int = DEFAULT_MAX_STEPS
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS
    repeat_threshold: int = DEFAULT_REPEAT_THRESHOLD
    clock: Callable[[], float] = time.monotonic

    def __post_init__(self) -> None:
        """校验安全阀参数范围。"""
        if self.max_steps < 1:
            raise ValueError("max_steps 必须至少为 1")
        if isinstance(self.deadline_seconds, bool) or not math.isfinite(self.deadline_seconds):
            raise ValueError("deadline_seconds 必须是有限正数")
        if self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds 必须大于 0")
        if self.repeat_threshold < 1:
            raise ValueError("repeat_threshold 必须至少为 1")


ToolOutcome = ToolResult


class ToolExecutor(Protocol):
    """工具执行协议；S06 注册表负责适配，调用方需保证可取消。"""

    def schemas(self) -> list[ToolSchema]:
        """返回本轮冻结的工具 Schema。"""
        ...

    async def execute(self, call: ToolCall) -> ToolOutcome:
        """执行一次工具调用；实现方负责结构化错误。"""
        ...


@dataclass(frozen=True)
class _ToolContext:
    executor: ToolExecutor
    policy: LoopPolicy
    deadline: float


@dataclass
class _LoopState:
    usage: Usage = field(default_factory=Usage)
    trace: list[ThoughtStep] = field(default_factory=list)
    tool_traces: list[ToolCallTrace] = field(default_factory=list)
    tool_calls: int = 0
    step: int = 0
    last_signature: str | None = None
    repeat_count: int = 0


async def run_react_loop(
    llm_client: LLMClient,
    messages: list[Message],
    tool_executor: ToolExecutor | None,
    policy: LoopPolicy | None = None,
    tools_snapshot: Sequence[ToolSchema] | None = None,
) -> AgentResult:
    """运行至最终文本；安全阀终止时返回 truncated 结果而不抛异常。"""
    active_policy = policy if policy is not None else LoopPolicy()
    deadline = _deadline_at(active_policy)
    tools = list(tools_snapshot) if tools_snapshot is not None else None
    if tools is None and tool_executor is not None:
        tools = tool_executor.schemas()
    state = _LoopState()
    while True:
        remaining = _remaining(deadline, active_policy.clock)
        if remaining <= 0:
            return _truncated_result(state, "deadline")
        state.step += 1
        try:
            response = await _request(llm_client, messages, tools, remaining)
        except TimeoutError:
            return _truncated_result(state, "deadline")
        state.usage = _add_usage(state.usage, response.usage)
        reasoning_present = bool(response.reasoning_content)
        if response.tool_calls:
            if tool_executor is None:
                raise LLMProtocolError("未配置工具执行器，不能处理 tool_calls")
            messages.append(_assistant_message(response))
            context = _ToolContext(tool_executor, active_policy, deadline)
            result = await _process_tools(
                response.tool_calls,
                messages,
                context,
                state,
                reasoning_present,
            )
            if result is not None:
                return result
            if state.step >= active_policy.max_steps:
                return _truncated_result(state, "max_steps")
            continue
        return _finish(response, messages, state, reasoning_present)


async def _request(
    llm_client: LLMClient,
    messages: list[Message],
    tools: list[ToolSchema] | None,
    remaining: float,
) -> LLMResponse:
    return await asyncio.wait_for(llm_client.chat(messages, tools=tools), remaining)


async def _process_tools(
    calls: list[ToolCall],
    messages: list[Message],
    context: _ToolContext,
    state: _LoopState,
    reasoning_present: bool,
) -> AgentResult | None:
    step_traces: list[ToolCallTrace] = []
    for index, call in enumerate(calls):
        remaining = _remaining(context.deadline, context.policy.clock)
        if remaining <= 0:
            _fill_cancelled(calls[index:], "deadline", messages, state, step_traces)
            _append_tool_step(state, step_traces, reasoning_present)
            return _truncated_result(state, "deadline")
        outcome, timed_out = await _execute_tool(context.executor, call, remaining)
        _append_tool(call, outcome, messages, state, step_traces)
        if timed_out:
            _fill_cancelled(calls[index + 1 :], "deadline", messages, state, step_traces)
            _append_tool_step(state, step_traces, reasoning_present)
            return _truncated_result(state, "deadline")
        _record_repeat(state, call, outcome)
        if state.repeat_count >= context.policy.repeat_threshold:
            _fill_cancelled(calls[index + 1 :], "repeat", messages, state, step_traces)
            _append_tool_step(state, step_traces, reasoning_present)
            return _truncated_result(state, "repeat")
    _append_tool_step(state, step_traces, reasoning_present)
    return None


async def _execute_tool(
    executor: ToolExecutor,
    call: ToolCall,
    remaining: float,
) -> tuple[ToolOutcome, bool]:
    if call.error_code is not None:
        return ToolOutcome(False, f"工具参数不合法：{call.error_code}", call.error_code), False
    scope = asyncio.timeout(remaining)
    try:
        async with scope:
            return await executor.execute(call), False
    except TimeoutError:
        if scope.expired():
            return ToolOutcome(False, "工具执行超时", "deadline"), True
        return ToolOutcome(False, "工具执行失败", "tool_execution_error"), False
    except Exception:
        return ToolOutcome(False, "工具执行失败", "tool_execution_error"), False


def _finish(
    response: LLMResponse,
    messages: list[Message],
    state: _LoopState,
    reasoning_present: bool,
) -> AgentResult:
    if response.content is None or not response.content.strip():
        raise LLMEmptyResponseError("模型没有返回有效答案")
    messages.append(_assistant_message(response))
    state.trace.append(
        ThoughtStep(
            step=state.step,
            decision="final",
            thought="返回最终答案",
            reasoning_present=reasoning_present,
        )
    )
    return AgentResult(
        reply=response.content,
        steps=state.step,
        usage=state.usage,
        trace=tuple(state.trace),
        tool_calls=state.tool_calls,
        tool_traces=tuple(state.tool_traces),
        truncated=False,
        termination_reason=None,
    )


def _truncated_result(state: _LoopState, reason: TerminationReason) -> AgentResult:
    return AgentResult(
        reply=_SAFETY_MESSAGES[reason],
        steps=max(state.step, 1),
        usage=state.usage,
        trace=tuple(state.trace),
        tool_calls=state.tool_calls,
        tool_traces=tuple(state.tool_traces),
        truncated=True,
        termination_reason=reason,
    )


def _assistant_message(response: LLMResponse) -> Message:
    return Message(
        role="assistant",
        content=response.content,
        tool_calls=response.tool_calls,
        reasoning_content=response.reasoning_content,
    )


def _append_tool(
    call: ToolCall,
    outcome: ToolOutcome,
    messages: list[Message],
    state: _LoopState,
    step_traces: list[ToolCallTrace],
) -> None:
    messages.append(Message(role="tool", content=outcome.content, tool_call_id=call.id))
    item = _tool_trace(call, outcome)
    step_traces.append(item)
    state.tool_traces.append(item)
    state.tool_calls += 1


def _fill_cancelled(
    calls: list[ToolCall],
    reason: str,
    messages: list[Message],
    state: _LoopState,
    step_traces: list[ToolCallTrace],
) -> None:
    content = "工具调用已取消" if reason == "deadline" else "重复调用已取消"
    for call in calls:
        _append_tool(call, ToolOutcome(False, content, reason), messages, state, step_traces)


def _append_tool_step(
    state: _LoopState,
    step_traces: list[ToolCallTrace],
    reasoning_present: bool,
) -> None:
    names = ", ".join(trace.tool for trace in step_traces)
    state.trace.append(
        ThoughtStep(
            step=state.step,
            decision="tool_call",
            thought=f"调用工具 {names}",
            reasoning_present=reasoning_present,
            tool_calls=tuple(step_traces),
        )
    )


def _record_repeat(state: _LoopState, call: ToolCall, outcome: ToolOutcome) -> None:
    if call.error_code is not None or not outcome.ok:
        state.last_signature = None
        state.repeat_count = 0
        return
    signature = _signature(call)
    if signature == state.last_signature:
        state.repeat_count += 1
    else:
        state.last_signature = signature
        state.repeat_count = 1


def _signature(call: ToolCall) -> str:
    args = json.dumps(call.arguments or {}, sort_keys=True, ensure_ascii=False, default=str)
    return f"{call.name}:{args}"


def _deadline_at(policy: LoopPolicy) -> float:
    return policy.clock() + policy.deadline_seconds


def _remaining(deadline: float, clock: Callable[[], float]) -> float:
    return deadline - clock()


def _add_usage(total: Usage, item: Usage) -> Usage:
    return Usage(
        prompt_tokens=total.prompt_tokens + item.prompt_tokens,
        completion_tokens=total.completion_tokens + item.completion_tokens,
        total_tokens=total.total_tokens + item.total_tokens,
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
