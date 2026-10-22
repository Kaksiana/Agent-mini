## Why

S02 第二次复验指出：默认 `on_retry=None` 时重试事件仍被丢弃；异常测试仍比较类名字符串；thinking+tools 用例未回传 assistant reasoning；`mypy agent_mini tests` 有 15 条错误而 README 未纳入 tests。

## What Changes

- `HttpLLMClient` 默认在客户端内记录 `RetryEvent`，`retry_events` 提供快照；`on_retry` 仅作为可选外部订阅。
- 异常测试改为 `pytest.raises(具体异常类)`。
- thinking+tools 测试改为两轮，第二请求同时携带 assistant reasoning、tool_calls、tools 与 thinking.enabled。
- 修复测试类型错误，README/规范门禁改为 `mypy agent_mini tests`。

## Capabilities

### Modified Capabilities

- `llm-client`: 默认重试事件记录。

## Impact

- 修改 `llm/client.py`、4 个契约测试、README、OpenSpec 门禁引用与 S02 复验记录。
- 不新增依赖，不实现日志系统或 Runtime。
