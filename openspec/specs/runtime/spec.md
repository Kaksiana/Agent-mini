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
