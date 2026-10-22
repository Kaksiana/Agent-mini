"""S00 包骨架导入测试。"""

import importlib

SUBPACKAGES = [
    "agent_mini.config",
    "agent_mini.llm",
    "agent_mini.runtime",
    "agent_mini.tools",
    "agent_mini.tools.builtin",
    "agent_mini.memory",
    "agent_mini.context",
    "agent_mini.systemdb",
    "agent_mini.interface",
    "agent_mini.observability",
]


def test_all_design_subpackages_are_importable() -> None:
    """DESIGN §2.2 的子包应全部可导入。"""
    for name in SUBPACKAGES:
        module = importlib.import_module(name)
        assert module.__name__ == name
