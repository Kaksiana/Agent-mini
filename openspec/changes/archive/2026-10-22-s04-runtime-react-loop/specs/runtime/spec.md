## ADDED Requirements

### Requirement: S04 ReAct 工具循环

`Agent` MUST 接受可选的 `ToolExecutor` 并循环调用 `LLMClient.chat`，直到收到无 tool_calls 的最终文本。有 executor 时 MUST 将 `schemas()` 传给每次请求；无 executor 时收到 tool_calls MUST 抛 `LLMProtocolError`。S04 MUST NOT 实现 `max_steps`、deadline、重复检测或 `truncated`。

#### Scenario: 两步工具收敛

- **WHEN** 第 1 次响应返回 tool_calls，第 2 次返回非空文本
- **THEN** `steps=2`，最终 `reply` 为第 2 次文本，工具只执行一次

#### Scenario: 多工具与伴随正文

- **WHEN** 响应同时含 content 与多个 tool_calls
- **THEN** 不提前返回 content，按原顺序执行全部工具并回灌

### Requirement: 消息配对

每次 tool_calls MUST 先写入 assistant 消息，再按原顺序为每个 call_id 写入一条 tool 消息；MUST NOT 出现孤立 tool 消息或遗漏 call_id。

#### Scenario: 两个调用

- **WHEN** 响应含两个 call_id
- **THEN** messages 中出现 1 条 assistant(tool_calls) 和 2 条对应 tool(call_id)

### Requirement: ThoughtStep 与隐私

每个 LLM 响应 MUST 产生一条冻结 `ThoughtStep`，字段恰为 `step/decision/thought/thought_source/reasoning_present/tool_calls/error_code`。`thought_source` MUST 为 `runtime_summary`；`reasoning_content` MUST NOT 出现在 `AgentResult`、`ThoughtStep`、`ToolCallTrace` 或公开 trace；工具参数敏感键与 observation 脱敏并截断到 200 字符。

#### Scenario: 工具步骤轨迹

- **WHEN** 一次响应执行工具
- **THEN** trace 的 decision=tool_call，tool_calls 含 call_id/tool/args/ok/error_code/observation，reasoning_present 只保留布尔值

### Requirement: AgentResult 增量

`AgentResult` MUST 保留 `reply/steps/usage`，并新增 `trace: tuple[ThoughtStep, ...]`、`tool_calls: int`、`tool_traces: tuple[ToolCallTrace, ...]`；`usage` MUST 为所有 LLM 调用之和，`reply` MUST 仍只表示最终文本。

#### Scenario: 结果字段

- **WHEN** 两步工具循环完成
- **THEN** reply/steps/usage/trace/tool_calls/tool_traces 均可读，trace 长度等于 LLM 调用次数

### Requirement: 工具错误结构化回灌

未知工具、参数/Schema/JSON 错误和执行异常 MUST 转为带原 call_id 的 tool 消息；无效调用 MUST NOT 执行 handler；模型可基于错误结果继续修正。

#### Scenario: 无效参数后修正

- **WHEN** 第 1 步参数非法、第 2 步合法
- **THEN** 第 1 条 tool 消息含 invalid_arguments，handler 未执行；第 2 步成功收敛
