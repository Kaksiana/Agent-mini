## ADDED Requirements

### Requirement: StoredRound 与 POSIX 发布

Memory MUST 使用冻结 StoredRound 表示轮次；Redis 读写 MUST 经该模型。write_file POSIX MUST 使用 dir_fd/O_DIRECTORY/O_NOFOLLOW 与 linkat/renameat 发布；Windows MUST 使用目录句柄锁定。

#### Scenario: StoredRound 元数据

- **WHEN** 读取轮次
- **THEN** round_id/messages/truncated/termination_reason 可访问

#### Scenario: POSIX 父目录 symlink

- **WHEN** POSIX 父目录被替换为 symlink
- **THEN** path_escape，外部文件不变
