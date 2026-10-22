## Context

参见 S04-report P0-01/P1-01..05。修复只触及 Runtime 公共结果边界、测试与累计规格，不扩展 S05/S06 行为。

## Decisions

- **统一脱敏函数**：`loop._sanitize_public_text` 处理 Known secret、Bearer、`sk-*`、敏感键值对；参数沿用结构化 key 脱敏，结果文本走模式脱敏。
- **单一常量**：`MAX_OBSERVATION_CHARS` 只保留在 `result.py`，loop 引用；结果模型仍作最后截断。
- **错误链测试**：三步脚本“非法/未知 → 合法 tool_call → final”，断言 handler 仅合法调用执行、两条 trace 失败/成功。
- **执行异常**：executor 抛异常 → `tool_execution_error` tool 消息 → final；异常不逃逸。
- **累计规格**：MODIFIED runtime S03/AgentResult 条款；Purpose 直接更新为 S03+S04。
- **流程例外**：S04 change 已于 `78e9aee` 归档，后续测试在 `20807ce`/`16973e2`；本 change 显式承接，不改归档目录。

## Risks / Trade-offs

- [模式脱敏可能过度替换普通文本] → 仅匹配高风险键名/token 模式；保留可读 observation。
- [深冻结未完成] → 列为 S06 前技术债，本 change 不做深层 copy。
- [主循环仍 >50 行] → P2 记录，S05 接入策略钩子时拆分。
