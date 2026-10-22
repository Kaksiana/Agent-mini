## Context

参见 `proposal.md`、`Docs/DESIGN.md` §3.1/§3.7 与 ISSUE-024。S01 的客户端只有单次请求；S02 增加错误分类与可配置退避重试，不改变聊天请求/响应归一契约。

## Goals / Non-Goals

**Goals:**

- 以稳定异常类型覆盖 400/401/403/429/5xx、超时与连接错误。
- 429/5xx 最多 3 次请求，指数退避 + 抖动；4xx/超时/协议错误不重试。
- 用注入 sleep 让重试测试快速、确定、无真实等待。

**Non-Goals:**

- 不实现 Runtime 收敛、工具重试或 HTTP 错误响应映射。
- 不把 `LLMError` 迁移到 `AgentError`（S20，ISSUE-024）。
- 不实现配置加载；重试参数由构造器提供默认值。

## Decisions

- **总尝试次数 3**：与 TC-L2-004 的“共 3 次请求”一致；2 次重试。
- **退避公式**：`0.5 * 2^(retry_index-1) + random.uniform(0, 0.1)`；抖动上界固定，保证间隔单调递增。
- **异常继承临时根**：新增异常全部继承 `LLMError`；S20 统一迁移。
- **sleep 注入**：默认 `asyncio.sleep`；测试注入记录型协程，不产生真实等待。
- **httpx 捕获顺序**：先 `TimeoutException`，再其他 `RequestError`，避免超时被误分类为连接错误。

## Risks / Trade-offs

- [真实服务 5xx 重试可能放大负载] → 最多 2 次重试，且仅对 429/5xx。
- [抖动导致测试不稳定] → 只断言区间与单调性，不依赖随机具体值。
- [临时 LLMError 根在 S20 迁移] → ISSUE-024 记录引用点和工作量。
