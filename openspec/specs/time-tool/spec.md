# time-tool Specification

## Purpose
定义 time 工具契约：默认 Asia/Shanghai、指定 IANA、timezone/tz 兼容、可注入 now_provider、invalid_timezone 结构化错误。

## Requirements

### Requirement: 默认与指定时区

time MUST 支持可选 `timezone`；未传入时使用 `DEFAULT_TIMEZONE="Asia/Shanghai"`；handler MUST 兼容 TC 的 `tz` 关键字且 `timezone` 优先。输出 MUST 含 ISO8601 时间戳与时区名。

#### Scenario: 默认时区

- **WHEN** 不传时区
- **THEN** 返回 Asia/Shanghai 的 ISO8601（+08:00）与时区名

#### Scenario: 指定 UTC

- **WHEN** 传 `tz="UTC"`
- **THEN** 返回 +00:00 与时区名 UTC

### Requirement: 非法时区

不存在的 IANA 名、空串、错误大小写、非字符串 MUST 返回 `invalid_timezone`，不得抛异常。

#### Scenario: Mars/Base

- **WHEN** 传入 `Mars/Base`
- **THEN** 返回 ToolResult(ok=False,error_code=invalid_timezone)

### Requirement: 确定性时间注入

handler MUST 支持 `now_provider(ZoneInfo) -> datetime` 注入；默认用 `datetime.now(zone)`；注入不得进入模型 Schema 或 Runtime。

#### Scenario: 固定时间

- **WHEN** now_provider 返回固定 UTC 时间
- **THEN** 输出可被确定性断言

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
