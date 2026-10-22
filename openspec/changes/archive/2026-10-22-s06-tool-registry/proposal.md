## Why

S04 Runtime 只有 `ToolExecutor` 测试替身，尚无真实注册、pydantic Schema 与参数校验。S06 需要提供统一 `ToolSpec`/`ToolRegistry`/`@tool`，并让 Runtime 能消费注册表；不实现任何具体工具。

## What Changes

- `tools/registry.py`：`ToolResult`（唯一执行结果、成功/失败不变量）、`ToolContext`（预留会话/trace）、`ToolSpec`、`ToolRegistry`、`@tool`。
- Schema 由 pydantic `params_model` 生成，`schemas()` 输出 OpenAI `ToolSchema`。
- 同名注册抛 `DuplicateToolError`；参数校验失败返回 `invalid_arguments`；handler 异常转 `ToolResult(ok=False)`。
- `runtime/registry_adapter.py` 把 `ToolRegistry` 适配为 S04 `ToolExecutor`；Runtime 不导入具体工具。
- 修复 P2-04：Runtime `ToolOutcome` 复用 `ToolResult`；ToolCallTrace args 只读/防御性副本。
- 不实现 S07–S12 工具、S10 沙箱、S09 会话状态。

## Capabilities

### New Capabilities

- `tool-registry`: 工具注册、pydantic Schema、参数校验与执行结果契约。

### Modified Capabilities

- `runtime`: Registry 适配器接入 ToolExecutor。

## Impact

- 修改 `tools/registry.py`、`runtime/{loop,registry_adapter}.py`、P2-04 相关模型；新增 S06 测试。
- 不新增依赖。
