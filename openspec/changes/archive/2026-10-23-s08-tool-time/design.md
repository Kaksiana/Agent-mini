## Context

S06 提供 `@tool`/ToolResult；S07 使用模块导入注册。Time 工具需要可测试时钟，但不把测试注入暴露给模型。

## Decisions

- **默认时区**：`DEFAULT_TIMEZONE="Asia/Shanghai"` 具名常量；S21 配置层接管，不在 S08 引入 config。
- **参数**：`TimeArgs.timezone: str | None` 是唯一 Schema 字段；handler `current_time(timezone=None, tz=None, now_provider=None)` 兼容 TC 的 `tz`，`timezone` 优先，`tz` 不进入 Schema。
- **时区解析**：`ZoneInfo(name)`；空串/大小写错误/NotFound/TypeError/ValueError 统一 `invalid_timezone`。
- **时间注入**：`now_provider` 默认 None → `datetime.now(zone)`；返回 naive 时补 tzinfo，aware 时 astimezone。
- **输出**：`f"{dt.isoformat()} {zone_name}"`。
- **注册**：`@tool("time", ...)` 默认 registry。
