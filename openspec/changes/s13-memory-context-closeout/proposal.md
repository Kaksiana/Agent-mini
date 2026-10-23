## Why

S13 报告要求 session_id 保留 sandbox 上下文、Memory 模型/校验/坏记录处理、安全阀写回与真实集成测试闭环。

## What Changes

- `RegistryExecutor.bind_request` 保留 sandbox_root/max_file_size，只替换 session/trace。
- ShortTermMemory：MULTI/EXEC、参数/session 校验、坏轮次跳过、写回超时可注入、metadata。
- S13 测试移至 tests/integration；M2 demo 标记 integration，unmarked=0。
- search name 异常结构化；S13 文档/统计修正。
