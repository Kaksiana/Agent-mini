## Context

参见 `proposal.md` 与 ISSUE-018。editable install 直接指向源码目录，无法证明 wheel 是否包含非 Python 文件；本次以构建产物为最终判定对象。

## Goals / Non-Goals

**Goals:**

- 让 `schema.sql` 进入 wheel。
- 用测试锁定 DESIGN §2.2 文件清单与占位模块内容约束。
- 保持现有导入、版本与依赖行为不变。

**Non-Goals:**

- 不实现 `schema.sql` 的表结构，内容仍为“待 S17 落地”注释。
- 不引入构建依赖或改变构建后端。
- 不把 wheel 构建放进默认单元测试；构建产物用验收命令检查。

## Decisions

- **使用 `[tool.setuptools.package-data]`**：setuptools 不会自动收录非 Python 文件，显式声明 `agent_mini.systemdb = ["schema.sql"]`。
- **测试读取 `pyproject.toml`**：用标准库 `tomllib` 验证 package-data，避免在单元测试中启动完整构建。
- **AST 检查占位模块**：断言每个占位 `.py` 只有模块 docstring，防止后续阶段误把实现塞进骨架文件。
- **结构测试使用显式文件清单**：与 DESIGN §2.2 一一对应，避免 `rglob` 掩盖缺失文件。

## Risks / Trade-offs

- [package-data 路径写错] → 构建 wheel 后用 `zipfile` 实际核对。
- [占位模块测试误伤后续实现] → 测试只扫描 S00 占位文件清单，后续阶段实现时同步调整测试与规格。
