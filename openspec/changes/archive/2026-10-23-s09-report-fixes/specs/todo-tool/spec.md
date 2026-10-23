## ADDED Requirements

### Requirement: Registry 类型与完整 Schema

todo 完整 Schema MUST NOT 含 session_id；非法 action MUST 在 Registry 路径返回 invalid_action；index MUST 只接受严格 integer，字符串/浮点/bool MUST 返回 invalid_arguments。

#### Scenario: 完整 Schema

- **WHEN** 序列化 todo Schema
- **THEN** 不含 session_id

#### Scenario: 非法 action

- **WHEN** Registry 收到 action=bogus
- **THEN** invalid_action

#### Scenario: 严格 index

- **WHEN** Registry 收到 index="1"/1.5/True
- **THEN** invalid_arguments

### Requirement: 隔离与快照

A/B 完成互不影响；伪造 session_id MUST 无副作用；Store 返回的元素 MUST 是快照，外部修改不得改变存储。

#### Scenario: 跨会话 complete

- **WHEN** A complete 后查 B
- **THEN** B 仍 open

#### Scenario: 伪造无副作用

- **WHEN** 带 session_id 参数调用被拒后 list
- **THEN** 原会话列表不变
