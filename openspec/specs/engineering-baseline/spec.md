# engineering-baseline Specification

## Purpose

提供 S00 可安装、可导入、可查询版本并具备 pytest/ruff/mypy 门禁的最小工程基线，不包含任何 Agent 业务能力。

## Requirements

### Requirement: 包可安装且可导入

项目 MUST 提供 PEP 621 元数据，使 `pip install -e .` 在 Python 3.11+ 环境成功，并能导入顶层包 `agent_mini`。

#### Scenario: 可编辑安装后导入

- **WHEN** 在仓库根目录执行 `pip install -e .`
- **THEN** 命令成功，且 `python -c "import agent_mini"` 退出码为 0

### Requirement: 版本查询

包 MUST 提供非空的 `agent_mini.__version__`，并通过公共版本查询入口返回同一版本值。

#### Scenario: 查询版本

- **WHEN** 调用 `agent_mini.get_version()`
- **THEN** 返回非空字符串，且与 `agent_mini.__version__` 相等

### Requirement: 工程检查配置

仓库 MUST 在 `pyproject.toml` 中配置 pytest、ruff 与 mypy，并在 `README.md` 记录可执行的安装、测试和静态检查命令。

#### Scenario: 静态检查与测试命令可用

- **WHEN** 开发者按 `README.md` 执行 `pytest`、`ruff check` 与 `mypy agent_mini`
- **THEN** 命令可运行，ruff 零告警，mypy 无错误

### Requirement: TC-SMOKE-001 工程 smoke

测试套件 MUST 包含 TC-SMOKE-001，验证导入包与版本查询，且不访问网络或存储。

#### Scenario: 运行 smoke 用例

- **WHEN** 执行 `pytest`
- **THEN** TC-SMOKE-001 通过，且测试进程无外部依赖访问
