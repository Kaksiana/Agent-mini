## Context

参见 `Docs/S02-report.md` §11。默认生产路径没有事件接收者，导致“可观察”只在调用方主动订阅时成立。采用客户端自有记录列表，不引入日志依赖。

## Decisions

- **客户端自有记录**：`_retry_events` 始终 append，`retry_events` 返回 tuple 快照。
- **回调保持可选**：`on_retry` 用于外部订阅；回调异常策略不变，S19 再决定隔离。
- **具体异常断言**：测试直接使用 `LLMBadRequestError`、`LLMAuthError`、`LLMTimeoutError` 等类型。
- **测试类型门禁**：修复 15 条 mypy 错误，README 改为 `mypy agent_mini tests`。

## Risks / Trade-offs

- [记录列表随客户端生命周期增长] → S02 客户端请求量有限；后续如需按请求隔离，可在 S03+ 增加 reset/step 边界。
- [tests 纳入 mypy 增加维护成本] → 以显式 cast/类型标注解决，避免 `# type: ignore`。
