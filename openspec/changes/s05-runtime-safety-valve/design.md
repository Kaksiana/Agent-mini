## Context

S04 的 `run_react_loop` 无参数、无上限且超过 50 行；S05 需要先参数化/拆分，再实现安全阀。PLR0915/PLR0912 已通过命名规则启用，当前函数未触发 lint 阈值。

## Decisions

- **前置重构**：新增 `LoopPolicy`（默认不限制）并把请求、工具批次、结果构造拆成 helper；行为不变，先提交。
- **默认值**：`DEFAULT_MAX_STEPS=8`、`DEFAULT_DEADLINE_SECONDS=120.0`、`DEFAULT_REPEAT_THRESHOLD=3`；集中常量。
- **终止原因**：`max_steps|deadline|repeat` 放 `AgentResult.termination_reason`；`ThoughtStep` 不新增字段，trace 长度仍等于 LLM 调用次数。
- **重复判定**：连续签名（name + sort_keys JSON args）达到阈值；不同签名重置。
- **Deadline**：自 run 启动计时；每个 LLM/工具调用前检查剩余，`asyncio.wait_for` 取消挂起调用；超时 outcome 为 deadline，补齐其余 call。
- **文案**：三条固定文案集中定义，不拼接动态原因。
- **S05 边界**：不实现 S06 注册表、Memory/Context/HTTP/真实 API；TC-L4-008 留 S18。

## Risks / Trade-offs

- [取消工具可能不响应] → `wait_for` 取消；S06 实现需保证可取消。
- [max_steps 与工具批次边界] → 完成当前批次后停止；deadline/repeat 中途触发时补齐剩余 call。
- [P2-01 函数长度] → 前置拆分与安全阀 helper，保持可读。
