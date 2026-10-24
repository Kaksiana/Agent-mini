## ADDED Requirements

### Requirement: 统一异常与映射

所有业务异常 MUST 继承 AgentError，携带稳定 code/http_status；HTTP MUST 由统一处理器映射并复用脱敏。

#### Scenario: 4xx 与 5xx

- **WHEN** 抛出 AgentError 子类
- **THEN** 响应 code 与日志 code 一致，4xx WARNING、5xx ERROR
