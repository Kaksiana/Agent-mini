## Why

S03 只支持无工具单轮直答。S04 必须实现 ReAct 工具循环、assistant/tool 消息配对、ThoughtStep 决策轨迹、工具错误回灌与增量 `AgentResult`，同时清理 S03 的 `LLMProtocolError` 过载语义，并为 S05 安全阀保留边界。

## What Changes

- `runtime/loop.py` 实现工具循环，定义 `ToolExecutor` Protocol 与 `ToolOutcome`；S04 只用测试替身，不实现 `tools/`。
- `AgentResult` 增量字段：`trace`、`tool_calls`、`tool_traces`；保持 `reply/steps/usage` 语义。
- 新增冻结 `ThoughtStep`/`ToolCallTrace`，实现 runtime_summary、reasoning_present、参数脱敏与 200 字符截断。
- 工具错误（未知工具、Schema/JSON 错误、执行异常）结构化回灌；assistant(tool_calls) 与 tool(call_id) 顺序配对。
- `LLMProtocolError` 只保留协议/结构/无 executor 请求契约语义；有 executor 时工具调用进入循环。
- S04 不实现 `max_steps`、deadline、重复检测或 truncated；循环无强制上限，S05 接入。

## Capabilities

### Modified Capabilities

- `runtime`: 增加 S04 工具循环、ThoughtStep、ToolCallTrace、AgentResult 增量字段。

## Impact

- 修改 `agent_mini/runtime/{agent,loop,result}.py`；新增 `tests/unit/test_react_loop.py`。
- 更新 DESIGN/TESTING/PLAN/ISSUE/MEMORY/PROMPT/README、runtime 规格。
- 不新增依赖；不修改 `llm/`、`tools/`、`memory/`、`context/`。
