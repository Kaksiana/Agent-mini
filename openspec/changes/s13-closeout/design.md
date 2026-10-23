## Context

S13 报告要求关闭 P0/P1。POSIX 测试在当前 Windows 环境 skip，登记 ISSUE。

## Decisions

- POSIX `_posix_publish`：root fd + 每级 O_DIRECTORY|O_NOFOLLOW；临时 O_EXCL|O_NOFOLLOW；link/rename dir_fd；失败清理。
- StoredRound dataclass frozen；Redis JSON 字段不变。
- TC-L3-015 使用 Agent→Registry→search，断言 not_configured trace；TC-L3-006 保留 calculator。
- 覆盖率豁免：POSIX-only 代码以 pragma 排除，总覆盖率 95.76%，<97.04，登记 ISSUE-040。
- 测试移动 integration；M2 demo 标记 integration；unmarked=0。
