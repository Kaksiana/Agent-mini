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

### Requirement: 包骨架符合设计目录

包 MUST 包含 `Docs/DESIGN.md` §2.2 列出的全部子包与占位模块；每个子包 SHALL 含 `__init__.py`，占位模块 MUST 仅含中文 docstring 或为空，不得包含业务实现。

#### Scenario: 所有子包可导入

- **WHEN** 依次导入 `config`、`llm`、`runtime`、`tools`、`tools.builtin`、`memory`、`context`、`systemdb`、`interface`、`observability`
- **THEN** 所有导入成功，且不触发网络、存储或业务逻辑

#### Scenario: 设计模块文件齐全

- **WHEN** 对照 `Docs/DESIGN.md` §2.2 检查 `agent_mini/`
- **THEN** 所有列出的子包、`__init__.py` 与模块文件均存在，占位文件不含函数、类或业务逻辑

#### Scenario: 版本入口保持可用

- **WHEN** 在骨架补齐后调用 `agent_mini.get_version()`
- **THEN** 仍返回非空版本字符串，且与 `agent_mini.__version__` 相等

### Requirement: 构建产物包含完整骨架

构建产物 MUST 包含 `Docs/DESIGN.md` §2.2 列出的全部 `agent_mini/` 文件（含 `systemdb/schema.sql`）；占位模块 MUST 仅含模块级中文 docstring，不得包含 `import`、函数或类。

#### Scenario: wheel 包含全部骨架文件

- **WHEN** 构建 wheel 并列出其内容
- **THEN** `agent_mini/` 下全部 35 个设计文件均存在，包含 `systemdb/schema.sql`

#### Scenario: 占位模块仅含 docstring

- **WHEN** 解析所有占位 `.py` 文件的 AST
- **THEN** 每个文件只包含一个模块级字符串表达式，不含 `import`、`def` 或 `class`

#### Scenario: 打包配置可回归

- **WHEN** 检查 `pyproject.toml` 的 setuptools 配置
- **THEN** `agent_mini.systemdb` 的 package-data 显式包含 `schema.sql`
