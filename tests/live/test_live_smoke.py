"""LIVE-001/002/003：真实 DeepSeek 验收（RUN_LIVE=1 + .env Key）。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_mini.llm.client import HttpLLMClient
from agent_mini.llm.models import Message, ModelConfig
from agent_mini.runtime.agent import Agent
from agent_mini.runtime.registry_adapter import RegistryExecutor
from agent_mini.tools import builtin as _builtin
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = [pytest.mark.live, pytest.mark.e2e]
_ = _builtin
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path(".env")
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@pytest.fixture
def live_key() -> str:
    values = _read_env()
    key = os.environ.get("DEEPSEEK_API_KEY") or values.get("DEEPSEEK_API_KEY")
    enabled = os.environ.get("RUN_LIVE") == "1" or values.get("RUN_LIVE") == "1"
    if not enabled or not key:
        pytest.skip("RUN_LIVE=1 与 DEEPSEEK_API_KEY 未配置")
    return key


def _client(key: str, thinking: bool = False) -> HttpLLMClient:
    return HttpLLMClient(
        ModelConfig(base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL, timeout=60.0),
        key,
        thinking=thinking,
    )


async def test_live_001_direct_answer(live_key: str) -> None:
    response = await _client(live_key).chat(
        [Message(role="user", content="回答：1+1 等于几？只回答数字。")]
    )
    assert response.content is not None
    assert "2" in response.content
    assert response.usage.total_tokens > 0
    assert live_key not in response.content


async def test_live_002_real_tool_loop(live_key: str) -> None:
    agent = Agent(
        _client(live_key),
        tool_executor=RegistryExecutor(DEFAULT_REGISTRY),
    )
    result = await agent.run(
        "必须调用 calculator 工具计算 expression=2+2，然后回答结果。",
        session_id="live-tool",
    )
    assert result.reply
    assert any(trace.tool == "calculator" and trace.ok for trace in result.tool_traces)
    assert result.trace_id
    assert live_key not in result.reply


async def test_live_003_thinking_mode(live_key: str) -> None:
    response = await _client(live_key, thinking=True).chat(
        [Message(role="user", content="用一句话说明 3*3 的结果。")],
        tools=None,
    )
    assert response.content is not None
    assert "9" in response.content
    assert live_key not in response.content
