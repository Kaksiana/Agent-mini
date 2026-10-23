# observability Specification

## Purpose
定义统一 JSON 日志、固定字段、trace/session ContextVar 与唯一脱敏过滤器。

## Requirements

### Requirement: JSON 日志与 trace

每条 agent_mini 日志 MUST 为 JSON 行，含固定字段 ts/level/event/trace_id/session_id/step/duration_ms；trace_id MUST 通过 contextvars 跨 create_task。

#### Scenario: 工具请求日志

- **WHEN** 设置 trace 后记录事件
- **THEN** JSON 可解析，trace 一致

### Requirement: 唯一脱敏点

RedactionFilter MUST 过滤 api_key/authorization/password/cookie、Bearer、sk-*、reasoning_content；不得记录完整 prompt/content/tool arguments。

#### Scenario: 哨兵密钥

- **WHEN** 日志包含假密钥与 reasoning
- **THEN** 文本不含原值，仅 ***/redacted 标记

