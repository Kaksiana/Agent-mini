## ADDED Requirements

### Requirement: 五表与职责隔离

schema.sql MUST 幂等创建 sessions/models/tools/tool_invocations/request_metrics；models/tools 的 name MUST 唯一；MySQL MUST NOT 存储对话正文；启动 upsert MUST 不覆盖手工 enabled。

#### Scenario: 重复建表/启动

- **WHEN** 连续执行 schema 或重复登记模型工具
- **THEN** 表/行不重复，enabled 保留

### Requirement: 会话审计与异步降级

Agent MUST 在响应后异步写 session/审计/指标；失败 MUST 记录 systemdb.degraded 且不阻断；session MUST 更新 last_active_at/message_count/status。

#### Scenario: MySQL 不可用

- **WHEN** record_turn 抛异常
- **THEN** Agent 正常返回，日志含 systemdb.degraded
