## Context

LLMError 是 S01 临时根；S18 局部映射重复且无法覆盖 Tool/Sandbox/SystemDB。

## Decisions

- AgentError 含类级 code/http_status；子类覆盖。
- HTTP 仅注册 AgentError 与 Exception 两个业务处理器。
- ContextTooLarge 继承 ContextError，保留 code=CONTEXT_TOO_LARGE/status=400。
- 未知异常 500 INTERNAL_ERROR，响应不含类名/堆栈；日志 exc_info 经 Filter。
- 4xx WARNING、5xx ERROR。
