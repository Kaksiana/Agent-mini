## ADDED Requirements

### Requirement: 未配置显式失败

未配置 provider（NullProvider）时 search MUST 返回 `not_configured`，响应 MUST NOT 含任何 URL/标题/摘要/模拟结果。

#### Scenario: 未配置

- **WHEN** search("今天天气")
- **THEN** ok=False、not_configured，无伪造 URL/摘要

### Requirement: Provider 协议与注入

`SearchProvider` MUST 为异步 `search(query, limit) -> Sequence[SearchResult]`，结果含 title/url/snippet/source；provider MUST 通过模块级 configure 注入，默认 NullProvider；不得读取环境变量/API Key。

#### Scenario: 配置后透传

- **WHEN** 注入 fake provider
- **THEN** 返回其结果、provider 名称

### Requirement: 参数/异常/截断

空/超长 query → invalid_query；limit<1 或 >10 → invalid_limit；provider 异常 → provider_error；超时 → provider_timeout；畸形结果 → provider_result_invalid；结果超过 limit 或摘要超过 500 字符 MUST 截断并标记 truncated；空结果合法成功。

#### Scenario: 超时

- **WHEN** provider 超时
- **THEN** provider_timeout

#### Scenario: 截断

- **WHEN** provider 返回超过 limit 或超长摘要
- **THEN** truncated=true
