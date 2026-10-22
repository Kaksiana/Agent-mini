## Why

S04 的 ReAct 循环没有硬边界；模型或工具持续返回相同调用时会无限运行。S05 必须提供 max_steps、deadline、重复调用检测、truncated 与终止原因，并补齐中断时未完成的 tool_calls，支撑 M1 收口。

## What Changes

- 前置参数化/拆分 `run_react_loop`，默认不限制，行为不变；再实现 S05 安全阀。
- 新增 `LoopPolicy` 默认 `max_steps=8`、`deadline=120s`、`repeat_threshold=3`、可注入单调时钟。
- `AgentResult` 增量 `truncated: bool` 与 `termination_reason`，正常收敛 false/None。
- 固定三条终止文案；deadline 用 `asyncio.wait_for` 取消挂起的 LLM/工具调用；重复按连续 `(name,规范化 args)` 计数。
- 中断时为本批未完成调用补齐同 call_id 的取消/超时 tool 结果。

## Capabilities

### Modified Capabilities

- `runtime`: S05 安全阀、truncated/终止原因与中断补齐。

## Impact

- 修改 `runtime/{agent,loop,result}.py`、新增 S05 测试；更新 DESIGN/TESTING/PLAN/ISSUE/MEMORY/PROMPT/README。
- 不新增依赖；不实现 S06/S13–S18。
