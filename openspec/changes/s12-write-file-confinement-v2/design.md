## Context

Windows 无 dir_fd 的 renameat/linkat；用 CreateFileW 目录句柄 + share 不含 DELETE 防重命名/删除/替换。

## Decisions

- 锁定链 root 到 parent；CreateFileW `FILE_FLAG_BACKUP_SEMANTICS|OPEN_REPARSE_POINT`，share=READ|WRITE。
- GetFinalPathNameByHandle 对比解析路径；FileAttributeTagInfo 检查 reparse。
- 锁内 mkstemp/link/replace；失败仅 unlink 临时文件，不 unlink target。
- POSIX 仍路径操作，残余风险记录；后续以 dir_fd 补齐。
