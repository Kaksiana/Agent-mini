## Why

S12 报告发现 M2 无显式装载、畸形 provider 字段泄漏、S11 发布窗口仍可越界、TC-L3-006 未闭环、Prompt/演示缺失。需修复后恢复 M2。

## What Changes

- builtin `__init__` 显式导入六工具，干净进程测试。
- 严格校验 provider name 与 SearchResult 字段；Registry search not_configured 测试。
- write_file 发布后再做 containment，越界清理目标。
- README M2 演示；ISSUE-039 记录 search E2E 留后续。
