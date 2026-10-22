## Why

S00 是后续 S01–S21 的工程前置。当前仓库只有文档，没有可安装包、测试入口和静态检查配置，无法用 TDD 验证任何后续功能。

## What Changes

- 新增 PEP 621 `pyproject.toml`，声明 Python ≥3.11、包元数据、开发工具和 pytest/ruff/mypy 配置。
- 新增最小 `agent_mini` 包，只暴露 `__version__` 与 `get_version()`。
- 新增 `tests/unit/test_smoke.py`，覆盖 TC-SMOKE-001。
- 更新 `README.md` 的安装、测试与静态检查命令。
- 不引入运行时依赖，不实现任何 Agent 业务模块。

## Capabilities

### New Capabilities

- `engineering-baseline`: 提供可安装、可导入、可查询版本并具备 pytest/ruff/mypy 门禁的最小工程基线。

### Modified Capabilities

- 无。

## Impact

- 新增 `pyproject.toml`、`agent_mini/__init__.py`、`tests/unit/test_smoke.py`。
- 更新 `README.md`。
- 开发依赖仅 `pytest`、`ruff`、`mypy`；无运行时依赖。
- 不影响 S01–S21 的业务设计。
