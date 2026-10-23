## Why

S12 需要搜索能力抽象；未配置 provider 时必须显式 not_configured，严禁伪造搜索结果。TC-L3-006 实际是 calculator 集成，需记录追溯缺口。

## What Changes

- 新增 `search.py`：`SearchProvider` Protocol、`SearchResult`、`NullProvider`、`SearchArgs`、`@tool("search")`。
- 模块级 provider 注入（默认 NullProvider）；测试 fake 放 tests。
- 异步 provider + 超时；结果条数/摘要长度截断；异常结构化。
- 未配置返回 not_configured，不返回 URL/摘要。
- 不实现真实 provider/API Key/搜索 SDK；无新增依赖。
