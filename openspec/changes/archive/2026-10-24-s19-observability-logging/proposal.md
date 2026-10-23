## Why

S19 需要统一 JSON 日志、trace_id contextvar 与唯一脱敏过滤器，替换 S18 HTTP 临时脱敏。

## What Changes

- `observability.logging` JSON Formatter/RedactionFilter/configure_logging。
- 固定字段 ts/level/event/trace_id/session_id/step/duration_ms。
- HTTP 设置 trace context；迁移临时 `_redact` 到共享 `redact_text`。
- reasoning/content 不进入日志；敏感 key/Bearer/sk-* 统一过滤。
