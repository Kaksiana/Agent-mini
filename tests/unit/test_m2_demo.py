"""M2 离线演示：六工具装载、文件往返、search not_configured。"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_mini.tools.builtin.read_file import read_file
from agent_mini.tools.builtin.search import reset_search_provider, search
from agent_mini.tools.builtin.write_file import write_file
from agent_mini.tools.registry import ToolContext

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[2]
EXPECTED_TOOLS = {"calculator", "time", "todo", "read_file", "write_file", "search"}


def test_builtin_loader_registers_six_tools_in_clean_process() -> None:
    code = (
        "import json;"
        "import agent_mini.tools.builtin;"
        "from agent_mini.tools.registry import DEFAULT_REGISTRY;"
        "print(json.dumps(sorted(s['name'] for s in DEFAULT_REGISTRY.schemas())))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    names = set(json.loads(completed.stdout))

    assert names == EXPECTED_TOOLS


async def test_m2_demo_file_roundtrip_and_search_not_configured(tmp_path: Path) -> None:
    reset_search_provider()
    context = ToolContext("demo", "trace", sandbox_root=str(tmp_path))
    written = write_file("demo.txt", "hello\n", context=context)
    read = read_file("demo.txt", context=context)
    searched = await search("demo")

    assert written.ok is True
    assert json.loads(read.content)["content"] == "hello\n"
    assert searched.error_code == "not_configured"
