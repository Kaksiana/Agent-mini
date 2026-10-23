## Why

关闭 S13 未闭环项：POSIX 目录句柄发布、search 独立集成 TC、StoredRound 冻结模型、覆盖率/流程记录。

## What Changes

- POSIX 使用 dir_fd/O_DIRECTORY/O_NOFOLLOW/linkat/renameat；Windows 保留目录句柄锁定。
- 新增 TC-L3-015 search Agent 集成，关闭 ISSUE-039。
- 引入 StoredRound(round_id,messages,truncated,termination_reason)，Redis 读写经模型。
- 测试分层：S13 integration、M2 integration、unmarked=0。
- 覆盖率未达 97.04%，登记 ISSUE 豁免。
