## MODIFIED Requirements

### Requirement: AgentResult 字段与不可变性

`AgentResult` MUST 是冻结模型，包含 `reply: str`、`steps: int`、`usage: Usage`、`trace: tuple[ThoughtStep, ...]`、`tool_calls: int`、`tool_traces: tuple[ToolCallTrace, ...]`、`truncated: bool`、`termination_reason: Literal["max_steps","deadline","repeat"] | None`。`usage` MUST 为所有 LLM 调用之和，`reply` MUST 只表示最终文本（安全阀时取固定提示），`truncated` 正常收敛为 false、安全阀为 true；额外字段 MUST 被拒绝。

#### Scenario: 字段完整性

- **WHEN** 循环正常结束或触发安全阀
- **THEN** 既有字段可读，truncated/termination_reason 符合语义，修改字段失败

#### Scenario: 正常收敛字段

- **WHEN** 循环正常结束
- **THEN** truncated=false、termination_reason=None，既有字段语义不变

## ADDED Requirements

### Requirement: S05 循环安全阀

循环 MUST 在 `max_steps`（默认 8）、deadline（默认 120s）、连续重复调用（默认 3 次）任一触发时停止，返回固定提示、`truncated=true` 与对应 `termination_reason`；MUST NOT 抛出安全阀异常或继续请求模型。

#### Scenario: 达到最大步数

- **WHEN** max_steps=3 且模型每步都返回 tool_calls
- **THEN** 恰好 3 步后停止，truncated=true，reason=max_steps，提示固定文案

#### Scenario: 达到截止时间

- **WHEN** 工具调用挂起超过 deadline
- **THEN** 取消该调用，不再请求模型，truncated=true，reason=deadline

#### Scenario: 连续重复调用

- **WHEN** 相同 name+规范化 args 连续出现 3 次
- **THEN** 停止，truncated=true，reason=repeat

### Requirement: 中断时 tool_calls 补齐

安全阀在工具批次中间触发时，MUST 为本批未完成/未执行的 tool_calls 按原 call_id 顺序写入取消或超时 tool 消息与 ToolCallTrace，不得出现孤立 tool 消息。

#### Scenario: 批次中途 deadline

- **WHEN** 一次响应含两个 tool_calls，第一个超时
- **THEN** 第二个也写入同 call_id 的取消结果，messages 配对完整
