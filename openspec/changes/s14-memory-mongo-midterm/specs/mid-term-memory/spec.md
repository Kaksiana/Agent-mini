## ADDED Requirements

### Requirement: MongoDB 轮次持久化与检索

MidTermMemory MUST 以 StoredRound 为唯一轮次契约，写入 session_id/round_id/messages/truncated/termination_reason/created_at；MUST 创建幂等复合索引 (session_id, created_at desc)；检索 MUST 强制 session 过滤、时间倒序、可选 content 关键词，公开结果 MUST 不返回 reasoning_content。

#### Scenario: 跨会话隔离

- **WHEN** A/B 各有轮次并按 A 检索
- **THEN** 仅返回 A 的记录

#### Scenario: 公开 reasoning 隔离

- **WHEN** 公开检索含 reasoning 的轮次
- **THEN** reasoning_content 为空，私有模式可读取

### Requirement: 响应后异步写回

Agent MUST 在响应返回后异步写 Mongo；Mongo 失败/超时 MUST 记录 memory.degraded 且不影响响应；Redis 写回顺序保持响应前同步。

#### Scenario: Mongo 失败

- **WHEN** append 抛异常
- **THEN** Agent 正常返回，日志含 memory.degraded
