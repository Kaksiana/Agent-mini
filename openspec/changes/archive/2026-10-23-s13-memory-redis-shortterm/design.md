## Context

S13 是 Memory 起点；S03 未引入 session_id。Redis 为异步客户端，测试用 fakeredis。

## Decisions

- **session_id**：`Agent.run(user_input, session_id: str | None = None)`；旧单参数不变；`AgentResult.session_id` 可选；不传 session 不写 Redis。
- **结构**：Redis List key `agent_mini:short_term:{session_id}:rounds`；元素 JSON `{round_id, messages:[message.model_dump(mode="json")]}`；禁止 pickle。
- **K/TTL**：DEFAULT_MAX_ROUNDS=10、DEFAULT_TTL_SECONDS=86400；每次 RPUSH 后 LTRIM -K -1、EXPIRE。
- **写回**：Agent 在 loop 返回后、返回前 `await short_term.append_round(...)`；round_id=uuid4().hex。
- **降级**：Memory 捕获连接/超时/序列化异常，logger warning `memory.degraded`，返回空/跳过，不抛出。
- **依赖**：redis>=7.4,<8；fakeredis>=2.23,<3 dev。
- **私有 reasoning**：随 Message JSON 持久化，读取时 model_validate 仅 assistant 合法，不进入公开 trace。
