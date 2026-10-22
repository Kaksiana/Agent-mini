## Why

S00 被错误标记为完成：当前 `agent_mini/` 只有顶层 `__init__.py` 与 `version.py`，未落地 `Docs/DESIGN.md` §2.2 规定的子包与占位模块，包骨架不完整。

## What Changes

- 新增 `config/`、`llm/`、`runtime/`、`tools/`、`memory/`、`context/`、`systemdb/`、`interface/`、`observability/` 子包及 `tools/builtin/`。
- 为每个子包新增 `__init__.py`，并为 DESIGN 列出的 23 个模块/文件新增仅含 docstring 或注释的占位内容。
- 新增子包可导入测试，保留原 TC-SMOKE-001。
- 将 `Docs/PLAN.md` 中 S00 回退为“进行中”，修正验收通过后再恢复“已完成”。
- 不修改现有 `agent_mini/__init__.py` 与 `agent_mini/version.py`，不实现任何业务逻辑，不新增依赖。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `engineering-baseline`: 新增“包骨架符合 DESIGN §2.2 目录结构”的规格要求。

## Impact

- 新增 10 个子包目录与 33 个骨架文件（10 个 `__init__.py`、23 个占位模块/文件）。
- 新增 1 个子包导入测试；原 smoke 测试不变。
- 不改变运行时行为、依赖清单或版本查询接口。
