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

### Requirement: 响应顶层结构硬化

客户端 MUST 在解析响应前确认顶层为 object；数组、字符串、数字或 null 顶层 MUST 抛 `LLMProtocolError`，不得泄漏 `AttributeError`。

#### Scenario: 非 object 顶层

- **WHEN** 上游返回 HTTP 200 且 JSON 顶层为数组、字符串、数字或 null
- **THEN** 客户端抛 `LLMProtocolError`，错误码为 `LLM_PROTOCOL_ERROR`，不返回响应对象

### Requirement: 请求保留字段不可覆盖

客户端 MUST 拒绝调用方覆盖 `model`、`messages`、`thinking`、`tools` 等受控字段；`model`/`thinking` 及非法 `tools` MUST 抛 `ValueError`，`messages` 重复传参由 Python 签名拒绝，拒绝必须发生在发送 HTTP 请求前。

#### Scenario: 尝试覆盖受控字段

- **WHEN** 调用方传入 `model`、`messages`、`thinking` 或 `tools` 作为额外参数
- **THEN** 调用被拒绝（`ValueError` 或签名 `TypeError`），且不发送请求

### Requirement: reasoning 仅限 assistant

`Message` MUST 只允许 assistant 角色携带 `reasoning_content`；user、system、tool 角色传入该字段 MUST 被模型校验拒绝。

#### Scenario: 非 assistant 携带 reasoning

- **WHEN** 构造 `role=user/system/tool` 且带 `reasoning_content` 的消息
- **THEN** 模型校验失败，消息不能被序列化到请求

### Requirement: HTTP 与 httpx 异常分类

客户端 MUST 将 `400` 映射为 `LLMBadRequestError`，`401/403` 映射为 `LLMAuthError`，`429` 映射为 `LLMRateLimitError`，`5xx` 映射为 `LLMServerError`，httpx 超时映射为 `LLMTimeoutError`，其他传输异常映射为 `LLMConnectionError`；所有异常 MUST 继承临时 `LLMError` 并携带稳定 `code/http_status`。临时根仅有效至 S19，S20 必须迁移为 `AgentError` 子类（ISSUE-024）。

#### Scenario: 4xx 分类

- **WHEN** 上游返回 400、401 或 403
- **THEN** 分别抛 `LLMBadRequestError`、`LLMAuthError`，且不重试

### Requirement: 429/5xx 退避重试

客户端 MUST 对 429 与 5xx 最多发起 3 次总请求，使用 0.5s 底数的指数退避并叠加不超过 0.1s 的抖动；不得重试 4xx、超时或协议错误；重试耗尽后 MUST 抛对应的限流/服务端异常。

#### Scenario: 重试后成功

- **WHEN** 上游依次返回 429、500、200
- **THEN** 共发起 3 次请求，最终返回成功响应，且两次退避间隔单调递增

#### Scenario: 重试耗尽

- **WHEN** 429 或 5xx 连续返回达到最大尝试次数
- **THEN** 抛 `LLMRateLimitError` 或 `LLMServerError`，不无限重试

### Requirement: 超时不重试

客户端 MUST 将 httpx 超时转换为 `LLMTimeoutError`，只发起 1 次请求，不挂起，并在错误消息中包含配置的超时秒数。

#### Scenario: 读超时

- **WHEN** 上游请求抛出 `httpx.ReadTimeout`
- **THEN** 只请求 1 次，抛 `LLMTimeoutError`，消息包含超时秒数

### Requirement: 重试策略有界且可观察

客户端 MUST 将公开重试策略的总尝试次数限制在 1–3；每次重试 MUST 通过结构化事件出口记录 attempt、max_attempts、status_code 与 delay_seconds，不得记录密钥或响应正文。退避达到上限后等待时长 MUST 非递减。

#### Scenario: 非法尝试次数被拒绝

- **WHEN** 构造 `RetryPolicy(max_attempts=0)`、负数、4、布尔值或非整数
- **THEN** 构造失败并给出可读错误，不发出任何请求

#### Scenario: 重试事件

- **WHEN** 429/500 触发两次重试
- **THEN** 事件依次记录 attempt=1/2、最大尝试次数、状态码与等待秒数

### Requirement: 超时配置传递与分类

客户端 MUST 将 `ModelConfig.timeout` 传入 HTTP 传输层；timeout 触发时 MUST 抛 `LLMTimeoutError` 且只发起 1 次请求，不得重试。测试 MUST 断言底层客户端 timeout 与配置一致，避免只验证异常转换。

#### Scenario: 超时配置与读超时

- **WHEN** 配置 timeout 并收到 `httpx.ReadTimeout`
- **THEN** 底层客户端 timeout 等于配置值，只请求 1 次并抛 `LLMTimeoutError`

### Requirement: 非预期 HTTP 状态分类

客户端 MUST 仅将明确的 4xx（400/401/403 等）映射为 BadRequest/Auth；3xx、非法或未知状态 MUST 映射为 `LLMProtocolError`，不得误报为 BadRequest，且不重试。

#### Scenario: 3xx 与未知状态

- **WHEN** 上游返回 302 或未知非 2xx/4xx/5xx 状态
- **THEN** 抛 `LLMProtocolError`，请求次数为 1，不进入重试

### Requirement: 默认重试事件记录

客户端 MUST 在每次重试时默认把 `RetryEvent` 追加到客户端自身的记录中；即使未配置 `on_retry`，调用方 MUST 能通过只读快照读取 attempt、max_attempts、status_code 与 delay_seconds。`on_retry` 仅作为可选外部订阅，不承担默认记录职责。

#### Scenario: 默认客户端重试

- **WHEN** 未传入 `on_retry` 的客户端经历 429、500 两次重试
- **THEN** `retry_events` 返回两条事件，attempt 依次为 1、2，状态码为 429、500

#### Scenario: 外部订阅

- **WHEN** 调用方提供 `on_retry`
- **THEN** 客户端仍保留默认记录，并额外调用回调
