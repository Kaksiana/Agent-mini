## Context

MySQL 8 + SQLAlchemy Core + asyncmy；本机 MySQL 服务不可启动，采用 SQLite 异步仓储测试 + MySQL schema 静态/环境门控。

## Decisions

- 五表字段按 DESIGN §3.9；`schema.sql` 使用 CREATE TABLE IF NOT EXISTS，DDL 演进暂以兼容追加 + 手工迁移说明。
- `SystemDBConfig(dsn,pool_size,pool_timeout_seconds,auto_create)`；构造注入 Repository，Agent 以 `with_system_db` 注入。
- upsert：SQLite `on_conflict_do_update` / MySQL `on_duplicate_key_update`；更新非键字段但不覆盖 enabled。
- session：首次 message_count=1，重复 upsert 累加；status=active；last_active_at 刷新。
- 异步：Agent `_background` 任务 + `drain` 限时等待；失败 `systemdb.degraded`。
- 测试：SQLite 覆盖 DDL/upsert/session/audit/isolation；真实 MySQL 由 `MYSQL_TEST_DSN` 环境门控（缺失 skip 并登记 ISSUE-043）。不静默通过。
- 降级事件：ensure_schema/upsert_models/upsert_tools/upsert_session/record_tool_invocation/record_metrics + Agent record_turn。
