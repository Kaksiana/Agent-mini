## ADDED Requirements

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
