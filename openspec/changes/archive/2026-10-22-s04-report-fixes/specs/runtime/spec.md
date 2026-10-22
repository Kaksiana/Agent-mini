## MODIFIED Requirements

### Requirement: S03 单轮直答接口

`Agent` MUST 通过构造器注入 `LLMClient`，并提供 `async def run(self, user_input: str) -> AgentResult`。无 `ToolExecutor` 的直答场景 MUST 只发送一条 `user` 消息、不传 tools、不接收 session_id，也不执行工具；S04 有 executor 时同一入口进入工具循环。`truncated` 延后 S05。

#### Scenario: 正常直答

- **WHEN** 无 executor 的客户端返回无 tool_calls 的非空文本
- **THEN** `Agent.run` 只调用一次 `chat`，返回 `steps=1` 且 `reply` 等于该文本

#### Scenario: 无工具路径

- **WHEN** 无 executor 的直答运行
- **THEN** 不执行工具；结果中 `trace` 为空、`tool_calls=0`、`tool_traces` 为空，且不存在 `truncated` 字段

#### Scenario: 空或纯空白内容

- **WHEN** 客户端返回 `content=None`、空字符串或纯空白且无 tool_calls
- **THEN** 抛 `LLMEmptyResponseError`，不得构造成功 `AgentResult`

#### Scenario: 意外 tool_calls

- **WHEN** 无 executor 的客户端返回非空 tool_calls，无论是否同时带 content
- **THEN** 抛 `LLMProtocolError`，不执行工具、不把 content 当最终回复

### Requirement: AgentResult 字段与不可变性

`AgentResult` MUST 是冻结模型，包含基线字段 `reply: str`、`steps: int`、`usage: Usage`，以及 S04 增量 `trace: tuple[ThoughtStep, ...]`、`tool_calls: int`、`tool_traces: tuple[ToolCallTrace, ...]`；`usage` MUST 为本轮所有 LLM 调用的 usage 之和，`reply` MUST 只表示最终文本且不混入 reasoning 或 trace。`reply` MUST 非空且非纯空白，`steps` MUST ≥ 1，额外字段 MUST 被拒绝。

#### Scenario: 字段完整性

- **WHEN** 直答或工具循环成功
- **THEN** 基线字段与 S04 增量字段可读，`usage` 等于各次响应之和，修改字段失败

## ADDED Requirements

### Requirement: 公开观测载荷脱敏

`ToolCallTrace.args` 与 `observation` MUST 在进入公开 `AgentResult` 前脱敏并截断到 200 字符。脱敏 MUST 同时处理调用参数敏感键、工具结果中独立出现的 `sk-*`、Bearer token、敏感 `key=value`/`key: value` 以及已知敏感值；不得只依赖参数中的 secret。

#### Scenario: 工具结果独立含密钥

- **WHEN** 调用参数不含秘密，但 executor 返回 `sk-...` 或 `token=...`
- **THEN** `AgentResult`/`ToolCallTrace` 中不出现原文，observation 仍截断到 200 字符

#### Scenario: 敏感参数

- **WHEN** 参数含 `api_key`、`authorization`、`cookie` 等
- **THEN** 公开 args 中对应值替换为 `***`
