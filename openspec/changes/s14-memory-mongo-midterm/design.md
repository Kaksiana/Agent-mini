## Context

S13 已有冻结 StoredRound；S14 不新建轮次结构。Mongo 异步驱动 pymongo，测试用 mongomock 适配器。

## Decisions

- 集合 `conversation_rounds`；索引 `session_created_desc`，字段 `(session_id 1, created_at -1)`，先查 index_information 再创建。
- 文档字段由 StoredRound 派生：session_id/round_id/messages/truncated/termination_reason/created_at。
- 关键词只匹配 `messages.content`，大小写不敏感，不匹配 reasoning；公开结果剥离 reasoning，`include_private=True` 保留。
- 写回：Redis 在 Agent.run 返回前 await；Mongo 用 asyncio.create_task，Agent 持有任务集合；失败/超时 5s 记录 `memory.degraded`。
- 依赖：pymongo>=4.9,<5；mongomock>=4.3,<5；不使用 motor/beanie。
- 边界：检索仅 session 内，不做全局搜索；S15/S16 负责 Context 裁剪。
