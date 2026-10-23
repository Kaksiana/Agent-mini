## ADDED Requirements

### Requirement: Registry 类型与 Schema 一致性

非字符串 `timezone` 经 Registry MUST 返回 `invalid_timezone`；模型完整 Schema MUST NOT 暴露不支持的 `tz` 别名。Windows 安装 MUST 声明 `tzdata` 数据依赖。

#### Scenario: Registry 非字符串

- **WHEN** Registry 收到 `{"timezone":123}`
- **THEN** 返回 invalid_timezone

#### Scenario: 完整 Schema

- **WHEN** 序列化 time Schema
- **THEN** 不含 tz 别名说明

### Requirement: 确定性固定时钟

固定 `now_provider` 测试 MUST 断言完整 ISO8601 与时区名；naive/aware 两种返回 MUST 有确定转换。

#### Scenario: 固定 UTC

- **WHEN** provider 固定为 2026-01-01T00:00Z
- **THEN** 默认输出 2026-01-01T08:00:00+08:00 Asia/Shanghai
