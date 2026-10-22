## Why

S01 只完成单轮请求与协议归一；HTTP 状态、httpx 超时和网络异常尚未分类，429/5xx 没有退避重试。S02 需要在模型接入层建立稳定的错误边界与可测试的重试策略，供 S03+ Runtime 使用。

## What Changes

- 扩展 `llm/errors.py`：新增鉴权、请求错误、超时、限流、服务端与连接异常。
- 扩展 `HttpLLMClient.chat`：按 HTTP 状态与 httpx 异常分类；429/5xx 按指数退避 + 抖动重试，4xx 与超时不重试。
- 将重试次数、退避底数、抖动上界提取为具名常量，并支持注入 sleep 以便契约测试。
- 新增 TC-L2-004/005/006 契约测试。
- 保持 S01 的 `LLMError` 临时根，S20 再迁移到 `AgentError`（ISSUE-024）。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `llm-client`: 新增 HTTP/httpx 错误分类、429/5xx 重试与超时不重试契约。

## Impact

- 修改 `agent_mini/llm/{errors,client}.py`；新增 `tests/contract/test_llm_retry.py`、`test_llm_timeout.py`、`test_llm_http_errors.py`。
- 不新增依赖；复用 httpx/respx。
- 不实现 Runtime、工具、Memory、HTTP 入口或配置层。
