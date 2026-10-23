"""TC-L3-015：Agent→Registry→search 未配置集成。"""

import pytest

import agent_mini.tools.builtin as builtin
from agent_mini.llm import models as llm_models
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = pytest.mark.integration


class _SearchLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(
        self,
        messages: list[llm_models.Message],
        tools: list[llm_models.ToolSchema] | None = None,
        **params: object,
    ) -> llm_models.LLMResponse:
        self.calls += 1
        if self.calls == 1:
            call = llm_models.ToolCall(id="call_1", name="search", arguments={"query": "天气"})
            return llm_models.LLMResponse(
                tool_calls=[call],
                finish_reason="tool_calls",
                usage=llm_models.Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        return llm_models.LLMResponse(
            content="搜索未配置",
            finish_reason="stop",
            usage=llm_models.Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_search_via_agent_reports_not_configured() -> None:
    _ = builtin
    result = await Agent(_SearchLLM(), RegistryExecutor(DEFAULT_REGISTRY)).run("hi")

    assert result.reply == "搜索未配置"
    assert len(result.tool_traces) == 1
    assert result.tool_traces[0].tool == "search"
    assert result.tool_traces[0].error_code == "not_configured"
