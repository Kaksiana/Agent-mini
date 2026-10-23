## Why

S15 需要把 system、工具摘要、中期摘要、短时历史与当前用户消息拼成请求，并计算可复现的 token 预算；只拼接与计数，不做裁剪。

## What Changes

- `ContextPayload`：messages、tools_snapshot、message_tokens、tool_schema_tokens、protocol_overhead_tokens、estimated_input_tokens、budget。
- `TokenCounter`：tiktoken cl100k_base、规范化 JSON、协议开销、10% 安全余量、字符降级。
- `ContextBuilder`：严格顺序；读取 ShortTermStore/MidTermStore 的 StoredRound；tools_snapshot 原引用复用。
- 新增 tiktoken 运行依赖。
- 不实现 S16 裁剪/丢弃/ContextTooLarge。
