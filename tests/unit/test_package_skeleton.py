"""S00 包骨架导入与结构测试。"""

import ast
import importlib
from importlib import resources
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "agent_mini"

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

DESIGN_FILES = [
    "__init__.py",
    "version.py",
    "config/__init__.py",
    "config/models.py",
    "config/loader.py",
    "config/container.py",
    "llm/__init__.py",
    "llm/client.py",
    "llm/models.py",
    "llm/errors.py",
    "runtime/__init__.py",
    "runtime/agent.py",
    "runtime/loop.py",
    "runtime/registry_adapter.py",
    "runtime/result.py",
    "tools/__init__.py",
    "tools/registry.py",
    "tools/sandbox.py",
    "tools/builtin/__init__.py",
    "tools/builtin/calculator.py",
    "tools/builtin/time_tool.py",
    "tools/builtin/todo.py",
    "tools/builtin/read_file.py",
    "tools/builtin/write_file.py",
    "tools/builtin/search.py",
    "memory/__init__.py",
    "memory/base.py",
    "memory/short_term.py",
    "memory/mid_term.py",
    "context/__init__.py",
    "context/builder.py",
    "context/window.py",
    "context/token_counter.py",
    "context/window.py",
    "systemdb/__init__.py",
    "systemdb/schema.sql",
    "systemdb/repository.py",
    "systemdb/models.py",
    "interface/__init__.py",
    "interface/http.py",
    "observability/__init__.py",
    "observability/logging.py",
    "observability/errors.py",
    "observability/errors.py",
]

NON_PLACEHOLDER_MODULES = {
    "__init__.py",
    "version.py",
    "llm/client.py",
    "llm/errors.py",
    "llm/models.py",
    "runtime/agent.py",
    "runtime/loop.py",
    "runtime/registry_adapter.py",
    "runtime/result.py",
    "tools/registry.py",
    "tools/sandbox.py",
    "tools/builtin/__init__.py",
    "tools/builtin/calculator.py",
    "tools/builtin/time_tool.py",
    "tools/builtin/todo.py",
    "tools/builtin/read_file.py",
    "tools/builtin/write_file.py",
    "tools/builtin/search.py",
    "memory/short_term.py",
    "memory/mid_term.py",
    "context/builder.py",
    "context/window.py",
    "context/token_counter.py",
    "memory/base.py",
    "systemdb/models.py",
    "systemdb/repository.py",
    "interface/http.py",
    "observability/logging.py",
    "observability/errors.py",
}

PLACEHOLDER_MODULES = [
    path for path in DESIGN_FILES if path.endswith(".py") and path not in NON_PLACEHOLDER_MODULES
]


def test_all_design_subpackages_are_importable() -> None:
    """DESIGN §2.2 的子包应全部可导入。"""
    for name in SUBPACKAGES:
        module = importlib.import_module(name)
        assert module.__name__ == name


def test_design_structure_is_complete() -> None:
    """DESIGN §2.2 的文件应全部存在。"""
    missing = [path for path in DESIGN_FILES if not (PACKAGE_ROOT / path).is_file()]
    assert missing == []


def test_placeholder_modules_contain_only_docstring() -> None:
    """占位模块只允许模块级中文 docstring。"""
    for path in PLACEHOLDER_MODULES:
        module = ast.parse((PACKAGE_ROOT / path).read_text(encoding="utf-8"))
        assert len(module.body) == 1, path
        node = module.body[0]
        assert isinstance(node, ast.Expr), path
        assert isinstance(node.value, ast.Constant), path
        assert isinstance(node.value.value, str), path
        assert any("\u4e00" <= char <= "\u9fff" for char in node.value.value), path


def test_schema_sql_has_five_idempotent_tables() -> None:
    """schema.sql 包含五表且使用 IF NOT EXISTS。"""
    schema = (PACKAGE_ROOT / "systemdb/schema.sql").read_text(encoding="utf-8")
    for table in ("sessions", "models", "tools", "tool_invocations", "request_metrics"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert schema.count("CREATE TABLE IF NOT EXISTS") == 5


def test_schema_sql_is_available_as_package_data() -> None:
    """schema.sql 应能通过包资源访问。"""
    schema = resources.files("agent_mini.systemdb").joinpath("schema.sql")
    assert schema.is_file()
