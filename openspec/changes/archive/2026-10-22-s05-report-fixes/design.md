## Context

S05 报告 P1-01..09。修复只改 Runtime 安全阀、测试、累计规格与过程记录；不重写已归档 change。

## Decisions

- **本地 TimeoutError**：`asyncio.timeout` 上下文 + `expired()` 区分等待器超时与 coroutine 自身异常；本地异常归 tool_execution_error。
- **重复签名**：仅成功执行调用参与；invalid_arguments 不计；name+sort_keys JSON；不同签名重置。
- **有限 deadline**：`math.isfinite` 且 >0，拒绝 bool；`_deadline_at` 入口第一时间计算，再取 schemas。
- **steps**：保留尝试调用计数，LLM 超时不再回退。
- **TC-L1-029 矩阵**：工具/LLM deadline、非有限值、签名规范化/重置、非法→合法空对象。
- **规格/流程**：新 change 修累计 runtime；M1 仅在 P1 修复后恢复；记录历史缺证，不伪造。

## Risks / Trade-offs

- [asyncio.timeout 仅 3.11+] → 项目目标 Python 3.11+，可接受。
- [schemas 同步阻塞无法取消] → 入口先计时；S06 注册表需明确同步边界。
