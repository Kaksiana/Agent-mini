## Context

S10 报告 P1-01..05 与 P2-01/02/04。修复只涉及 sandbox/read_file/测试与文档。

## Decisions

- **路径分段**：同时用 `PurePosixPath`/`PureWindowsPath` 拆段；`..` 直接 path_escape；隐藏段按两种分隔符；设备名集合拒绝。
- **codec**：`codecs.lookup` 后检查 `_is_text_encoding`；空编码不回落默认；decode 捕 LookupError。
- **有界读取**：`open("rb").read(limit+1)`；长度 >limit 即 file_too_large；stat 大小仍先检查。
- **错误码**：FileNotFoundError→file_not_found；其他 OSError→file_read_error。
- **测试**：移除 skip；Windows 无 symlink 权限时 junction 失败则测试失败而非跳过。
- **流程**：新 change 承接归档后修复；测试数与声明由实际执行重新计算。
