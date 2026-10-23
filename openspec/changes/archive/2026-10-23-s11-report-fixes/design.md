## Context

S11 报告 P0-01/02、P1-01..04。修复只涉及 write_file/sandbox 常量/测试/文档。

## Decisions

- **原子不覆盖**：临时文件同目录写入+fsync；overwrite=false 用 `os.link(temp,target)`；EEXIST→file_exists；成功后 unlink temp。overwrite=true 用 os.replace。
- **父目录竞态**：mkstemp 前、创建后、发布前均 `resolve().is_relative_to(root)`；失败 path_escape 并清理。仍不声称完全无竞态，但阻断可观测的 parent 替换。
- **设备名**：`COM1..COM9`/`LPT1..LPT9` 生成集合。
- **TC 映射**：TC-L4-002 仅 calculator；文件 E2E 待 S18。
- **记录**：Prompt 后补属历史偏差，ISSUE-038 记录。
