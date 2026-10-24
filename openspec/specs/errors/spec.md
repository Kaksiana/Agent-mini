# errors Specification

## Purpose
定义统一 AgentError 层级、稳定错误码、HTTP 状态映射、日志级别与脱敏响应的一致性约束。

## Requirements

### Requirement: 统一异常与映射

所有业务异常 MUST 继承 AgentError，携带稳定 code/http_status；HTTP MUST 由统一处理器映射并复用脱敏。

#### Scenario: 4xx 与 5xx

- **WHEN** 抛出 AgentError 子类
- **THEN** 响应 code 与日志 code 一致，4xx WARNING、5xx ERROR
