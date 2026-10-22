## ADDED Requirements

### Requirement: 默认重试事件记录

客户端 MUST 在每次重试时默认把 `RetryEvent` 追加到客户端自身的记录中；即使未配置 `on_retry`，调用方 MUST 能通过只读快照读取 attempt、max_attempts、status_code 与 delay_seconds。`on_retry` 仅作为可选外部订阅，不承担默认记录职责。

#### Scenario: 默认客户端重试

- **WHEN** 未传入 `on_retry` 的客户端经历 429、500 两次重试
- **THEN** `retry_events` 返回两条事件，attempt 依次为 1、2，状态码为 429、500

#### Scenario: 外部订阅

- **WHEN** 调用方提供 `on_retry`
- **THEN** 客户端仍保留默认记录，并额外调用回调
