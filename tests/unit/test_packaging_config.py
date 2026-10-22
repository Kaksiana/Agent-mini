"""打包配置测试。"""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

DEV_CONSTRAINTS = {
    "ruff": ">=0.17,<0.18",
    "mypy": ">=2.4,<2.5",
    "pytest-asyncio": ">=1.3,<1.4",
    "respx": ">=0.23,<0.24",
    "pytest-cov": ">=7.1,<7.2",
}


def test_systemdb_schema_is_declared_as_package_data() -> None:
    """schema.sql 必须声明为 agent_mini.systemdb 的包数据。"""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    package_data = config["tool"]["setuptools"]["package-data"]
    assert "schema.sql" in package_data["agent_mini.systemdb"]


def test_dev_tools_have_minor_bounds_and_pytest_cov() -> None:
    """dev 工具必须 pin 到 minor 兼容范围，并声明 pytest-cov。"""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = config["project"]["optional-dependencies"]["dev"]
    for name, constraint in DEV_CONSTRAINTS.items():
        assert any(requirement == f"{name}{constraint}" for requirement in dev)
