## ADDED Requirements

### Requirement: HTTP 与 httpx 异常分类

客户端 MUST 将 `400` 映射为 `LLMBadRequestError`，`401/403` 映射为 `LLMAuthError`，`429` 映射为 `LLMRateLimitError`，`5xx` 映射为 `LLMServerError`，httpx 超时映射为 `LLMTimeoutError`，其他传输异常映射为 `LLMConnectionError`；所有异常 MUST 继承临时 `LLMError` 并携带稳定 `code/http_status`。

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
