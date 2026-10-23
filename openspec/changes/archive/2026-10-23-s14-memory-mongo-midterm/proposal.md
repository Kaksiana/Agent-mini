## Why

S14 需要 MongoDB 中期持久化与检索，直接复用 S13 的 StoredRound，并在响应返回后异步写回，失败不阻断主链路。

## What Changes

- `MidTermMemory`：集合 `conversation_rounds`，字段由 StoredRound + session_id/created_at 派生。
- 复合索引 `(session_id, created_at desc)`，索引名常量，幂等创建。
- 检索强制 session 过滤、时间倒序、可选 content 关键词；公开结果剥离 reasoning。
- Agent 响应后异步写 Mongo，失败 `memory.degraded`。
- 新增 pymongo 运行依赖、mongomock dev 依赖。
