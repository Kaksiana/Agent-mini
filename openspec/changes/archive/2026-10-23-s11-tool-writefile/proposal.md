## Why

S11 需要在同一沙箱内安全写文件：默认不覆盖、原子替换、失败无残留。

## What Changes

- 新增 `write_file.py`：`WriteFileArgs(path, content, overwrite=False, encoding=None)`。
- 复用 `Sandbox.resolve`；父目录必须存在；不自动创建。
- 同目录临时文件 + `fsync` + `os.replace`；失败清理；默认不覆盖；显式 overwrite 才替换。
- 校验/编码/超限在打开临时文件前返回；写入失败清理临时文件。
- 不实现 search/Memory/HTTP，不改 Runtime。

## Capabilities

### New Capabilities

- `write-file`: 沙箱内原子写与覆盖保护。
