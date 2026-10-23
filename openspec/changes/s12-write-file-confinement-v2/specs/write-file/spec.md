## ADDED Requirements

### Requirement: 目录句柄锁定发布

write_file MUST 在 root→target parent 的目录句柄锁定期间完成临时文件创建与 link/replace；Windows MUST 不共享 DELETE 并校验最终路径与 reparse 属性；失败 MUST 只清理锁定目录内临时文件，MUST NOT 对重新解析的 target 做补偿删除。

#### Scenario: 父目录 junction

- **WHEN** 发布前父目录被替换为 root 外 junction
- **THEN** path_escape，外部文件不被删除/覆盖
