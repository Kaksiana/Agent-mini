## Context

S10 沙箱为 read_file 与 S11 write_file 共用。根目录不硬编码：`ToolContext.sandbox_root`（S06/S09 已有 context 注入）提供，`max_file_size` 可选覆盖。

## Decisions

- **根来源**：`ToolContext.sandbox_root: str | None`、`max_file_size: int | None`；不进入模型 Schema。S11 复用。
- **四步**：拒绝绝对路径（含 `PureWindowsPath`）/空/`.`；join+resolve；`is_relative_to(root.resolve())`；扩展名白名单（大小写敏感）+ 非隐藏 + 路径长度。
- **限制**：默认 1 MiB、扩展名 `.txt/.md/.json/.csv/.log/.py/.yaml/.yml`、禁止隐藏、空文件允许、路径 ≤240。
- **read_file**：先 stat 大小，再读 bytes；NUL → binary_file；decode 失败 → decode_error；返回 JSON `{content,size,encoding}`；保留换行。
- **TOCTOU**：resolve 后 open，未用 `O_NOFOLLOW`；仅承诺最小防护，残余竞态在 design 留痕；S10 不声称强原子性。
- **错误码**：absolute_path、path_escape、invalid_path、hidden_path、extension_not_allowed、path_too_long、file_not_found、file_too_large、binary_file、decode_error、invalid_encoding、missing_sandbox_root。
