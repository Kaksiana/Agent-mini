## Context

依据 DESIGN §3.2.3/§3.2.4、§3.3 与 S04 TCs。S04 只实现 Runtime 循环与测试替身协议；真实工具注册表、Memory、Context、安全阀和 HTTP 均延后。

## Goals / Non-Goals

**Goals:**

- 工具循环、消息配对、ThoughtStep、AgentResult 增量。
- 错误回灌、隐私脱敏、无 executor 的协议拒绝。
- 为 S05 留出循环接入点，但不实现终止阀。

**Non-Goals:**

- 不实现 S05 max_steps/deadline/repeat/truncated。
- 不实现 S06 注册表、真实工具或 Schema 生成。
- 不实现 S13–S16 Memory/Context 或 S18 HTTP。
- 不调用真实 API。

## Decisions

- **Protocol 位置**：`runtime/loop.py` 定义 `ToolExecutor` 与 `ToolOutcome`；S06 适配。
- **结果字段**：`AgentResult.trace`、`tool_calls`、`tool_traces` 默认空；`usage` 对每次 chat 求和。
- **ThoughtStep**：放在 `runtime/result.py`，冻结、extra=forbid；`ToolCallTrace` 同文件。
- **循环**：`while True` 直到 final；无 count/deadline 上限，S05 以包装器/参数接入。
- **隐私**：assistant 的 reasoning 只保留在 messages；公开 trace 仅布尔 `reasoning_present`；参数敏感键替换 `***`，observation 截断 200。
- **异常**：有 executor 时 tool_calls 正常处理；无 executor 时 tool_calls 仍抛 `LLMProtocolError`；结构非法也抛 `LLMProtocolError`。

## Risks / Trade-offs

- [无上限循环] → S04 测试替身有限；S05 必须接入硬边界。
- [ToolOutcome 为 Runtime 临时模型] → S06 适配真实 ToolResult，不把注册实现放入 runtime。
- [冻结模型浅冻结] → observation/args 由 runtime 生成，不在外部修改。
