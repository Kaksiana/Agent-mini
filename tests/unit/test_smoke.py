"""S00 工程 smoke 测试。"""

import pytest

import agent_mini

pytestmark = pytest.mark.unit


def test_import_package_version_query_returns_version() -> None:
    """导入包并通过公共入口查询版本。"""
    assert agent_mini.__version__
    assert agent_mini.get_version() == agent_mini.__version__
