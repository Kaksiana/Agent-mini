## Why

S05 报告发现 deadline 与重复检测存在可复现 P1：工具本地 TimeoutError 被误判为全局 deadline；非法参数与合法空对象签名碰撞；NaN/Infinity deadline 绕过；deadline 在 schemas 后计时；LLM deadline 少计 steps；TC-L1-029 覆盖不足；累计 runtime 规格与 M1 声明超前。

## What Changes

- 区分工具本地 `TimeoutError` 与等待器超时；本地异常归 `tool_execution_error` 并允许继续。
- 重复签名跳过 invalid_arguments，使用成功调用的 name+规范化 args；补重置/纠正测试。
- deadline 强制有限正数；在 `Agent.run`/loop 入口先建立；LLM 超时保留尝试步数。
- 补 LLM 挂起、非有限值、签名重置、非法→合法空对象等 TC-L1-029 子场景。
- 新 change 修复累计 runtime 规格；记录 S05 流程偏差，不重写历史；M1 恢复条件与离线演示命令。

## Capabilities

### Modified Capabilities

- `runtime`: deadline/重复/步数/累计 AgentResult 与 M1 演示契约。

## Impact

- 修改 `runtime/loop.py`、`result.py`、S05 测试、runtime 主规格、S05-report、PLAN/README/MEMORY/PROMPT/ISSUE。
- 不新增依赖；不实现 S06/S13–S18。
