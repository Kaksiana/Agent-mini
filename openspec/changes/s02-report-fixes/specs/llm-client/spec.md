## ADDED Requirements

### Requirement: 重试策略有界且可观察

客户端 MUST 将公开重试策略的总尝试次数限制在 1–3；每次重试 MUST 通过结构化事件出口记录 attempt、max_attempts、status_code 与 delay_seconds，不得记录密钥或响应正文。退避达到上限后等待时长 MUST 非递减。

#### Scenario: 非法尝试次数被拒绝

- **WHEN** 构造 `RetryPolicy(max_attempts=0)`、负数、4、布尔值或非整数
- **THEN** 构造失败并给出可读错误，不发出任何请求

#### Scenario: 重试事件

- **WHEN** 429/500 触发两次重试
- **THEN** 事件依次记录 attempt=1/2、最大尝试次数、状态码与等待秒数

### Requirement: 超时配置真正约束等待

客户端 MUST 将 `ModelConfig.timeout` 传入 HTTP 传输层；本地慢响应超过该超时后 MUST 在 timeout 上限附近抛 `LLMTimeoutError`，不得等待完整响应。

#### Scenario: 本地慢服务器

- **WHEN** 本地服务器延迟超过配置 timeout
- **THEN** 客户端在有限时间内抛 `LLMTimeoutError`，且只发起 1 次请求

### Requirement: 非预期 HTTP 状态分类

客户端 MUST 仅将明确的 4xx（400/401/403 等）映射为 BadRequest/Auth；3xx、非法或未知状态 MUST 映射为 `LLMProtocolError`，不得误报为 BadRequest，且不重试。

#### Scenario: 3xx 与未知状态

- **WHEN** 上游返回 302 或未知非 2xx/4xx/5xx 状态
- **THEN** 抛 `LLMProtocolError`，请求次数为 1，不进入重试
