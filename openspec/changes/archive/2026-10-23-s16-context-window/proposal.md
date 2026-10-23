## Why

S16 需要双触发的整轮裁剪，并在每次 LLM 出站前复核预算；最小集合仍超限时本地 ContextTooLarge。

## What Changes

- `window.fit_rounds`：轮次 > K 或 token > budget 触发，整轮丢弃最旧历史并重计数。
- `ContextPayload` 增加 rounds_before/after、tokens_before/after、dropped_rounds、trim_reason。
- Agent/loop 在每次 chat 前调用 ContextBuilder.fit；ContextTooLarge 不发请求。
- S15 的拼接、计数公式、tools_snapshot 语义保持。
