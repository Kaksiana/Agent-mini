## Context

S12 是 Tool 层最后一个工具；真实 provider 不交付。TC-L1-021 要求 not_configured；TC-L3-006 是 calculator 集成，不适用于 search。

## Decisions

- **协议**：async `SearchProvider.search(query, limit) -> Sequence[SearchResult]`；`SearchResult(title,url,snippet,source)` frozen dataclass；`name` property。
- **注入**：模块级 `configure_search_provider(provider)`/`reset_search_provider()`；默认 `NullProvider`；fake 只在 tests。
- **未配置**：`isinstance(provider, NullProvider)` → `not_configured`，绝不生成结果。
- **参数**：query 非空且 ≤200；limit 默认 5、1..10；超限 invalid_limit。
- **执行**：`asyncio.wait_for(provider.search(...), SEARCH_TIMEOUT_SECONDS=5)`；TimeoutError→provider_timeout；其他异常→provider_error；非 SearchResult 结构→provider_result_invalid。
- **截断**：结果最多 limit 条；snippet 最多 500 字符；任一截断 truncated=true。
- **输出**：JSON `{provider, truncated, results:[...]}`；空结果 ok=True/truncated=false。
- **依赖**：复用 asyncio/标准库；不新增 httpx 使用。
