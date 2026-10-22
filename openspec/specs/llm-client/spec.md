# llm-client Specification

## Purpose
提供 OpenAI Chat Completions 兼容的单轮 LLM 客户端，统一请求、响应、工具调用参数与可选 reasoning 的协议边界。

## Requirements

### Requirement: 单轮 Chat Completions 请求

客户端 MUST 向 `{base_url}/chat/completions` 发起 POST 请求，携带 `model`、`messages`、可选 `tools` 与 `Authorization` 头；默认 MUST 显式发送 `thinking.disabled`。

#### Scenario: 请求结构与鉴权

- **WHEN** 使用 base_url、model、messages 与一个工具 Schema 调用 `chat()`
- **THEN** 请求路径、`model`、`messages`、`tools[].function.name/parameters` 与 `Authorization: Bearer ***` 均正确

#### Scenario: 默认关闭思考

- **WHEN** 客户端未启用 thinking
- **THEN** 请求体显式包含 `thinking={"type":"disabled"}`

### Requirement: 响应归一

客户端 MUST 将响应归一为 `content`、`reasoning_content`、`tool_calls`、`usage` 与 `finish_reason`；缺失或 null 的 `tool_calls` 归一为空列表，缺失或 null 的 `reasoning_content` 保持 None。

#### Scenario: 文本响应

- **WHEN** 上游返回普通文本与 usage
- **THEN** `content` 正确、`tool_calls` 为空、`usage` 三个字段与响应一致

#### Scenario: 工具调用响应

- **WHEN** 上游返回一个合法 tool_call
- **THEN** 解析出一个 `ToolCall`，`arguments` 为 dict，`finish_reason=tool_calls`

### Requirement: 响应判别

客户端 MUST 将结构错误或未知终止原因映射为 `LLMProtocolError`，将 `length` 映射为 `LLMOutputTruncatedError`，将 `content_filter` 映射为 `LLMOutputRejectedError`，将无有效答案映射为 `LLMEmptyResponseError`。

#### Scenario: 非法与终止响应

- **WHEN** 响应缺少 choices、message 非法、调用 ID 重复/为空、终止原因矛盾或未知
- **THEN** 抛出 `LLMProtocolError`，不返回伪成功响应

#### Scenario: 空答案与截断

- **WHEN** 响应只有 reasoning/空白 content，或 finish_reason 为 length/content_filter
- **THEN** 分别抛出 `LLMEmptyResponseError`、`LLMOutputTruncatedError`、`LLMOutputRejectedError`

### Requirement: 工具参数严格解析

客户端 MUST 校验 tool_call ID 非空且唯一、function 结构合法，并将 arguments 严格解析为 JSON object；重复键、NaN/Infinity、非 object 顶层 MUST 被拒绝，并以 `invalid_arguments` 与原 call_id 保留结构化错误。

#### Scenario: 合法参数

- **WHEN** arguments 是合法 JSON object
- **THEN** `ToolCall.arguments` 为 dict，`error_code` 为空

#### Scenario: 非法参数

- **WHEN** arguments 为破损 JSON、数组、字符串、重复键或 NaN
- **THEN** 返回带原 call_id 的 `ToolCall(error_code="invalid_arguments", arguments=None)`，不执行工具

### Requirement: Thinking 与私有 Reasoning

thinking 启用时，客户端 MUST 在请求中保留并回传历史 assistant 消息的 `reasoning_content`；thinking 关闭时 MUST 不发送该字段，且不得从 content 猜测 reasoning。

#### Scenario: 回传历史 reasoning

- **WHEN** thinking 已启用且请求携带历史 assistant reasoning
- **THEN** 下一次请求体保留对应 `reasoning_content`

#### Scenario: 默认模式不发送 reasoning

- **WHEN** thinking 未启用
- **THEN** 请求体不包含 `reasoning_content`，响应中的 reasoning 仅保留在 `LLMResponse`
