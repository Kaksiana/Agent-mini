# MEMORY <!-- omit in toc -->

## 2026-10-21 — 文档评审修订

- 当前仅有需求/设计/测试/计划文档，S00–S21 未开始；不得将测试设计或真实 API 计划表述为已通过。
- LLM 分别解析 content、可选 reasoning_content、tool_calls；公开 thought 是带 runtime_summary 来源标记的决策摘要。思考工具模式必要的 reasoning 只在同 session 私有协议字段回传，不进入公开 trace、日志或 MySQL。
- 每次 LLM 出站前，统一计数实际 messages、完整 tools Schema 与协议开销；计数/发送复用 tools_snapshot。保留最多 K 个历史完整轮次，最小集合仍超预算时本地 CONTEXT_TOO_LARGE/400，不继续请求模型。
- Redis 按完整轮次保留；todo 的 session_id 由可信执行上下文注入，模型不能覆盖。新增双窗口、工具追问和真实 API 验收用例，功能用例共 75 个，另有 1 个工程 smoke。
- 真实 API 001/002 是交付门禁；启用思考模式时还需 003。密钥只从 DEEPSEEK_API_KEY 读取，文档仅保留脱敏占位；本轮未保存或验证用户提供的密钥。
