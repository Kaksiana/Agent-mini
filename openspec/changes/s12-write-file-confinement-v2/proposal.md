## Why

S13 报告指出 write_file 发布后补偿删除仍可破坏沙箱外文件。需要目录句柄锁定发布，关闭 S12 P0。

## What Changes

- Windows 锁定 root→parent 目录句柄，不共享 DELETE；校验句柄最终路径/reparse。
- 发布在锁内执行；失败只清理本目录临时文件；不再外部补偿删除。
- POSIX 仍以路径操作为限，记录残余；新增 junction/reparse 竞态测试。
