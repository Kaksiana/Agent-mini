"""打包配置测试。"""

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_systemdb_schema_is_declared_as_package_data() -> None:
    """schema.sql 必须声明为 agent_mini.systemdb 的包数据。"""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    package_data = config["tool"]["setuptools"]["package-data"]
    assert "schema.sql" in package_data["agent_mini.systemdb"]
