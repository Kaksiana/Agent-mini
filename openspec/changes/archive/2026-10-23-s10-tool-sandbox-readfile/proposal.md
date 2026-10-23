## Why

S10 需要文件访问沙箱与 read_file，阻断 `..`、绝对路径、符号链接逃逸，并限制大小/编码。

## What Changes

- `Sandbox(root, max_file_size)` 四步校验 + 隐藏/扩展名/路径长度限制。
- `read_file(path, encoding)` 从 `ToolContext.sandbox_root/max_file_size` 取根，返回内容+size/encoding；空文件正常，二进制/超限/解码失败结构化错误。
- `ToolContext` 增量 `sandbox_root`/`max_file_size`；不进入 Schema。
- 不实现 write_file/search/Memory/HTTP。
