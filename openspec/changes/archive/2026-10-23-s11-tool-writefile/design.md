## Context

S10 Sandbox 提供 root/限制/四步 resolve。S11 复用同一 Sandbox，不复制校验逻辑。

## Decisions

- **根/限制**：ToolContext.sandbox_root / max_file_size；与 read_file 同源。
- **父目录**：必须已存在且 resolve 在 root 内；不自动创建，否则 parent_not_found。
- **覆盖**：默认 false；exists 检查在临时文件前；true 时保留既有权限（chmod 既有 mode），否则默认 umask。
- **原子写**：tempfile.mkstemp(dir=target.parent, prefix=".write-", suffix=".tmp")；写入+flush+os.fsync；os.replace；失败 unlink temp。默认 fsync=True。
- **并发**：exists+replace 非原子，采用最小防护；并发写可能后写覆盖，S11 不宣称强 CAS。
- **编码**：仅 `_is_text_encoding`；先编码再检查字节数；空内容合法。
- **错误码**：missing_sandbox_root、invalid_encoding、file_exists、parent_not_found、file_too_large、file_write_error。
- **往返**：UTF-8 原始换行写入，read_file 保留原始。
