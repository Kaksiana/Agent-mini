## Why

S17 需要 MySQL 系统库承载会话、模型/工具登记、工具审计与请求指标，并与 Redis/Mongo 职责隔离；写入失败不得影响对话。

## What Changes

- `schema.sql`：sessions/models/tools/tool_invocations/request_metrics 五表，幂等 DDL。
- `SystemDBRepository`：SQLAlchemy Core + asyncmy；模型/工具幂等 upsert、session upsert、审计/指标写入。
- `SystemDBConfig` 与记录模型；`auto_create` 控制 DDL。
- Agent 响应后异步 `record_turn`，`drain` 限时等待；失败 `systemdb.degraded`。
- 测试：SQLite 异步覆盖仓储逻辑；MySQL 语义以 schema/环境门控，真实实例缺失登记 ISSUE。
