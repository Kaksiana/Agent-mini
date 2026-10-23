## Why

S18 是唯一对外入口，需要 POST /chat、健康检查、错误码映射、脱敏与无状态会话复用。

## What Changes

- FastAPI `create_app(agent, health_checks)`：/chat、/healthz。
- 请求/响应字段严格按 DESIGN §3.6；session_id 自动生成/复用。
- LLM/Context 异常映射 400/408/429/502/500；错误响应脱敏。
- Agent 增加可选 trace_id 贯穿 ToolContext/SystemDB。
- LIVE 用例仅 RUN_LIVE + DEEPSEEK_API_KEY 下运行。
