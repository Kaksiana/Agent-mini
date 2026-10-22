## ADDED Requirements

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
