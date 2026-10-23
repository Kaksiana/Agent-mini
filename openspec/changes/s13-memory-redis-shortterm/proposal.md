## Why

S13 需要 Redis 短时会话窗口，并在响应返回前同步写回完整轮次；S03 延后的 session_id 需正式引入且保持历史兼容。

## What Changes

- `Agent.run(user_input, session_id=None)` 增量参数；`AgentResult.session_id` 可选；不传 session 时旧行为不变。
- `ShortTermMemory`：Redis List、每元素完整轮次 JSON、LTRIM 最近 K 轮、EXPIRE TTL。
- Runtime 在 `run_react_loop` 后、返回前 `await append_round`；异常降级 `memory.degraded`。
- 新增 redis/fakeredis 依赖。
- 不实现 Mongo/Context/HTTP。
