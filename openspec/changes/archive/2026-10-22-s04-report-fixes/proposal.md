## Why

S04 报告判定不通过：公开 observation 可泄露独立于调用参数的工具结果秘密；错误修正链和执行异常回灌缺少正式测试；runtime 主规格仍保留 S03 排他字段；S04 归档后又补三步测试与红证据，流程未记录例外。

## What Changes

- 统一公开观测脱敏：参数敏感键、工具结果独立 secret、`sk-*`、Bearer、`key=value` 模式；先脱敏再截断。
- 补 TC-L1-028/TC-L2-009 的“失败→合法调用→收敛”链，以及执行异常回灌测试。
- 修订 runtime 主规格为 S03+S04 累计契约，删除 S03 排他字段断言。
- 新 change 记录归档后变更例外；逐 TC 记录红因/绿因。
- 统一 observation 长度常量，补 usage 分项与每次 tools 快照断言。

## Capabilities

### Modified Capabilities

- `runtime`: 发布载荷脱敏、累计 AgentResult、错误修正与异常回灌契约。

## Impact

- 修改 `runtime/loop.py`、`runtime/result.py`、S04 测试、runtime 主规格、S04-report、PROMPT/ISSUE。
- 不新增依赖；不实现 S05/S06/S13–S18。
