## Context

S15 已交付 ContextBuilder/TokenCounter/tools_snapshot；S16 只加裁剪与出站复核。

## Decisions

- 触发顺序：每轮先计算 over_rounds/over_tokens；任一成立丢弃最旧一轮；两者同时成立 reason=both；后续以最后一次触发为准。
- 当前轮：messages 最后一条 user 起；system/工具摘要/当前轮不可删。
- ContextTooLarge 在 fixed（prefix+current+tools）超预算或裁完仍超时抛出；异常属性 code=CONTEXT_TOO_LARGE、http_status=400、steps、truncated=True。
- payload 分项：rounds_before/after、tokens_before/after、dropped_rounds、trim_reason、message_tokens、tool_schema_tokens、protocol_overhead_tokens、budget。
- 日志：context.trimmed，字段与 payload 一致。
- 接入：Agent.with_context 创建 fit 回调，loop 每次 chat 前 `messages[:] = fit(messages)`；S15 快照 tuple 语义不变。
- K=10、事件名为具名常量。
