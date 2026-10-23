## Context

S12 报告 P0/P1。修复只涉及 loader/search/write_file 发布后检查/测试/文档。

## Decisions

- **loader**：builtin `__init__` 仅 docstring + re-export 六模块；导入即注册；subprocess 断言。
- **provider 严格性**：name 必须 str；每个 SearchResult 四字段 str；否则 provider_result_invalid。
- **write_file**：提交后再次 `_assert_inside(target, root)`；失败删除已提交目标并 path_escape。
- **TC**：TC-L3-006 保留 calculator；search 独立 E2E 留后续，ISSUE-039 记录。
- **M2 demo**：README 指向 test_m2_demo.py（六工具装载、文件往返、not_configured）。
