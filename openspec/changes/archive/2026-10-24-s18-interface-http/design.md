## Context

S13–S17 已提供 Memory/Context/SystemDB；S18 仅做 HTTP 入口与最小 trace 接入。

## Decisions

- `create_app(agent, health_checks)`；无进程内会话缓存，session_id 直接传 Agent，Redis/Mongo 恢复。
- 响应 trace 使用 ThoughtStep 公开字段；reasoning 不进入响应。
- 错误映射：RequestValidation/ContextTooLarge=400；LLMTimeout=408；LLMRateLimit=429；LLMError=502；其他=500。
- trace_id：HTTP UUID → Agent.run → ToolContext/SystemDB；AgentResult 回传。
- Key 只从 `DEEPSEEK_API_KEY` 读取；LIVE 需 RUN_LIVE=1，缺失 skip。
- 脱敏：错误/回复过滤 key 名值、Bearer、sk-*；healthz 不返回异常文本。
- 双窗口：复用 S13/S14，不新增回退逻辑；S15/S16 已读两存储。
