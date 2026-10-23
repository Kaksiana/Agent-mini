## ADDED Requirements

### Requirement: POST /chat 与健康检查

/chat MUST 接收 session_id?/message，返回 session_id/reply/steps/tool_calls/usage/trace/trace_id/truncated；session_id 未传 MUST 生成 UUID4；/healthz MUST 只返回依赖状态，不泄露 DSN/密钥。

#### Scenario: 纯对话

- **WHEN** POST /chat 纯文本
- **THEN** 200，字段完整，truncated=false

### Requirement: 错误映射与脱敏

MUST 映射 400 入参/ContextTooLarge、408 超时、429 限流、502 模型、500 内部；响应/日志 MUST 过滤 api_key/authorization/password/cookie/sk-/Bearer，reasoning MUST 不出现在公开响应。

#### Scenario: ContextTooLarge

- **WHEN** Agent 抛 ContextTooLarge
- **THEN** 400 code=CONTEXT_TOO_LARGE，无堆栈
