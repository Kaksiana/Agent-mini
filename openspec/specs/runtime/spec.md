# runtime Specification

## Purpose

定义 S03 Agent Runtime 的单轮直答契约：构造器注入 `LLMClient`、`Agent.run(user_input)` 一步返回、冻结 `AgentResult(reply/steps/usage)`，以及 LLM 异常原样传播。

## Requirements

### Requirement: S03 单轮直答接口

`Agent` MUST 通过构造器注入 `LLMClient`，并提供 `async def run(self, user_input: str) -> AgentResult`。S03 MUST 只发送一条 `user` 消息、不传 tools、不接收 session_id，也不实现工具循环、trace、truncated 或 Memory。

#### Scenario: 正常直答

- **WHEN** 注入的客户端返回无 tool_calls 的非空文本
- **THEN** `Agent.run` 只调用一次 `chat`，返回 `steps=1` 且 `reply` 等于该文本

#### Scenario: 无工具路径

- **WHEN** S03 运行
- **THEN** 不访问工具注册表、不执行工具，结果模型不包含 tool_calls/trace/truncated 字段

#### Scenario: 空或纯空白内容

- **WHEN** 客户端返回 `content=None`、空字符串或纯空白且无 tool_calls
- **THEN** 抛 `LLMEmptyResponseError`，不得构造成功 `AgentResult`

#### Scenario: 意外 tool_calls

- **WHEN** 客户端返回非空 tool_calls，无论是否同时带 content
- **THEN** 抛 `LLMProtocolError`，不执行工具、不把 content 当最终回复

### Requirement: AgentResult 字段与不可变性

`AgentResult` MUST 是冻结模型，且只包含 `reply: str`、`steps: int`、`usage: Usage`；`usage` MUST 直接来自 `LLMResponse.usage`，`reply` MUST 不混入 reasoning 或 trace。`reply` MUST 非空且非纯空白，`steps` MUST ≥ 1，额外字段 MUST 被拒绝。

#### Scenario: 字段完整性

- **WHEN** 直答成功
- **THEN** 字段集合恰为 reply/steps/usage，`usage` 与 LLM 响应相等，修改字段失败

### Requirement: LLM 异常原样传播

`Agent.run` MUST 将 `LLMError` 及其子类原样传播，不吞、不包装、不重试；`LLMEmptyResponseError` 与 `LLMTimeoutError` 必须保持类型和实例。

#### Scenario: 空响应

- **WHEN** 客户端抛 `LLMEmptyResponseError`
- **THEN** 同一异常实例传播到调用方

#### Scenario: LLM 异常

- **WHEN** 客户端抛 `LLMTimeoutError`
- **THEN** 同一异常实例传播，`chat` 只调用一次

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
