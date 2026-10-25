# M3 独立复验（2026-10-25）

> 性质：当前 Agent 只读执行，不含独立第三方评审；结论限于自动化证据。

## 命令

```bash
pytest tests/integration/test_m3_demo.py tests/integration/test_short_term.py \
  tests/integration/test_mid_term.py tests/integration/test_context_builder.py \
  tests/integration/test_context_window.py -q
```

## 结果

**51 passed**（1.73s）。

## 覆盖

- M3 demo：三轮只写当前轮、跨轮历史、12 轮裁到 10 轮。
- Redis 短时记忆：失败降级、TTL、整轮裁剪。
- Mongo 中期：索引、去重、降级、超时。
- ContextBuilder/Window：拼接、双触发裁剪、不可删减保留。

## 结论

M3 核心集成用例全绿；**未**做独立人工审阅，不把 M3 标为“独立复验完成”。

## 复审修复（2026-10-25）

独立评审列出的 4 项 P1 已修复：

1. `trim_reason` 无裁剪返回 `None`（`test_five_rounds_order_and_system_first` 断言）。
2. 跨存储合并以 short 顺序为主，避免 Mongo 部分写回导致 r2 排到 r3 后（`test_cross_store_merge_keeps_short_order`）。
3. `MidTermMemory.get_rounds` 首次调用 `ensure_indexes`，生产读取路径会建索引。
4. 容器 `with_context(include_reasoning=False)`，与 `HttpLLMClient(thinking=False)` 的实际发送一致。
5. P2 Mongo 脏文档改为逐条跳过（`_degraded("decode_document")`）。

仍剩余：P2 无真实 Redis+Mongo+ContextBuilder 全链路；P3 每轮 build+fit 重复读取 Memory。

当前 M3 门禁：**392 passed、1 skipped（Docker+LIVE 全量）**，覆盖率 94.60%。独立复审报告待子代理确认。

## 最终独立复核（2026-10-25）

子代理重跑 `tests/integration/test_context_builder.py`：**13 passed**；M3 五文件：**53 passed**。

- A：mid=[r2,r3]、short=[r1,r2,r3]（r1 Mongo 写失败）→ **r1,r2,r3 PASS**。
- B：mid=[r1,r2,r3]、short=[r1,r2]（r3 Redis 写失败）→ **r1,r2,r3 PASS**。

4 项 P1 全部闭合。

残留：P2 无真实 Redis+Mongo+ContextBuilder 全链路；P3 重复 build/fit、search_rounds 不建索引、Agent.close 不关客户端。

## P2/P3 收尾（2026-10-25）

- **P2 真实全链路关闭**：`test_real_redis_mongo_context_chain` 使用真实 Redis+Mongo 写入 r1/r2/r3（Mongo 缺 r2 模拟写失败），ContextBuilder 输出 r1,r2,r3。
- **P3 index 关闭**：`MidTermMemory.search_rounds` 首次调用 `ensure_indexes`；`_index_attempted` 防止故障时每轮重试。
- **P3 close 关闭**：`Agent.close()` 依次排空并调用 LLM/Short/Mid/SystemDB 的 `aclose/close`。
- **P3 重复 build/fit 未关闭**：尝试首轮复用 payload 会破坏 `test_fit_is_bounded_by_deadline` 的 deadline 语义，已回退；保留为已知 P3。
- 最终：M3 五文件 53 passed；全量 394 passed、1 skipped；覆盖率 94.72%。
