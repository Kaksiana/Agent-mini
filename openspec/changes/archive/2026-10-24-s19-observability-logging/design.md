## Context

S18 在 HTTP 内维护临时正则与 request.state trace；S19 改为 observability 单一实现。

## Decisions

- `TRACE_ID`/`SESSION_ID` ContextVar；HTTP 入口 set，create_task 自动继承。
- 固定字段缺失用 null/0；附加字段保留。
- Filter 在 Formatter 前执行：敏感 key → ***；content/prompt/arguments → `<redacted:len>`；文本正则过滤 Bearer/sk/敏感 key=value。
- 级别：INFO 正常事件、WARNING 降级、ERROR 不可恢复异常；S19 不新增异常分类。
- 事件名：http.chat、react.step、context.trimmed、memory.degraded、systemdb.degraded。
- duration_ms：HTTP 整请求 monotonic 起止；其他事件由调用点提供。
- S18 `_SECRET_PATTERNS`/`_redact` 删除，HTTP 调共享 `redact_text`。
