## Context

S06 报告 P1-01..07 与 P2。修复只触及注册表/结果模型/测试/过程记录；不实现具体工具。

## Decisions

- **启停**：`ToolRegistry(enabled: Mapping[str,bool] | None)`；`is_enabled(spec)` 以 enabled_key 查询，未配置默认启用；schemas/execute 统一过滤。
- **同步隔离**：`inspect.iscoroutinefunction` 分支；同步用 `asyncio.to_thread`，async 直接 await；to_thread 不可强杀线程，但事件循环/deadline 可返回。
- **额外参数**：pydantic 字段名白名单比较，不依赖模型 extra 配置。
- **返回类型**：只接受 ToolResult；其他含 None/str 均 `invalid_tool_result`。
- **元数据**：ToolSpec 注册期校验 name/description 非空、params_model 为 BaseModel 子类、handler callable、enabled_key 非空或 None。
- **深只读**：递归 mappingproxy/tuple；字段 serializer 还原普通 JSON。
- **流程**：新 change 承接；历史 Prompt 缺证不伪造，后续逐字记录。

## Risks / Trade-offs

- [to_thread 超时后线程可能继续] → 事件循环不再阻塞；真实工具需可取消/短操作，S10 再约束。
- [顶层字段白名单] → 嵌套模型 extra 行为仍由 pydantic 模型决定，S06 先固化顶层可信边界。
