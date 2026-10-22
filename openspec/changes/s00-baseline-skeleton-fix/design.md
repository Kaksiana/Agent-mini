## Context

参见 `proposal.md` 与 ISSUE-017。现有包只有 `agent_mini/__init__.py` 与 `agent_mini/version.py`；本次只补目录与占位文件，不改变版本接口和安装行为。

## Goals / Non-Goals

**Goals:**

- 按 `Docs/DESIGN.md` §2.2 建立 10 个子包与 23 个占位模块/文件。
- 用最小导入测试锁定骨架结构，避免再次漏建。
- 保持现有 `__init__.py`、`version.py` 与 TC-SMOKE-001 不变。

**Non-Goals:**

- 不实现 LLM、Runtime、Tool、Memory、Context、SystemDB、Interface、Observability、Config 业务逻辑。
- 不新增依赖，不调整构建或版本机制。
- 不为各子包设计公共 API；这些在后续阶段落地。

## Decisions

- **占位模块使用单行中文 docstring**：满足 ruff `D100` 与全局规范，同时不引入实现；比纯空文件更易读。
- **`tools/builtin/` 只建 `__init__.py`**：DESIGN 只规定该子包，具体工具文件在 S06–S12 落地，本次不提前创建。
- **`schema.sql` 使用注释占位**：明确“待 S17 落地”，避免空文件语义不明。
- **新增独立导入测试**：只验证子包可导入，不触碰业务行为；原 TC-SMOKE-001 保留。

## Risks / Trade-offs

- [占位 docstring 被误认为已实现] → 文案统一标注“占位，待 Sxx 落地”。
- [新增文件触发 ruff/mypy 问题] → 每个文件仅 docstring，实际运行 ruff、mypy、pytest 验证。
- [包结构再次与设计漂移] → 增加子包导入测试并在 ISSUE-017 记录预防措施。
