## Why

S06 报告发现 `enabled_key` 无启停行为、同步 handler 阻塞事件循环、额外参数被静默接受、任意返回值被包装成功；Prompt/TDD/OpenSpec 时序也不合规。S06 必须闭环后才能进入 S07。

## What Changes

- `ToolRegistry` 接受启停配置：禁用工具不出现在 schemas 且 execute 返回 `tool_disabled`。
- 同步 handler 通过 `asyncio.to_thread` 执行，避免阻塞事件循环；async handler 直接 await。
- 参数校验按 pydantic 字段白名单拒绝额外键；ToolSpec 注册期校验名称/描述/模型/handler/enabled_key。
- handler 仅允许返回 `ToolResult`；其他类型返回 `invalid_tool_result`。
- ToolResult 失败内容必须可读非空；ToolCallTrace.args 递归只读。
- 新 change 提醒流程：Prompt 逐字记录、红灯先于实现；不重写已归档 change。

## Capabilities

### Modified Capabilities

- `tool-registry`: 启停、异步执行、严格参数与返回契约。

## Impact

- 修改 `tools/registry.py`、`runtime/result.py`、S06 测试、tool-registry 主规格、S06-report/PROMPT。
- 不新增依赖；不实现具体工具。
