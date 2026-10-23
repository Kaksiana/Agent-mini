## Why

S10 报告发现 Windows 反斜杠隐藏段与任意 `..` 可绕过、非文本 codec 误判、stat 后文件增长绕过大小限制、skip 与计数矛盾、读取错误码过粗。

## What Changes

- 统一按 Windows/POSIX 分隔符拆段；任意 `..` 直接 path_escape；拒绝 Windows 保留设备名。
- 仅允许文本 codec；空编码/非文本编解码器返回 invalid_encoding；decode LookupError 兜底。
- 有界读取：最多读 limit+1，超过即 file_too_large，避免 stat 后增长全量载入。
- 区分 file_not_found 与 file_read_error；移除 pytest.skip。
- 修正测试计数与流程记录；新增 `s10-report-fixes` change。

## Capabilities

### Modified Capabilities

- `sandbox`: Windows 路径/设备名/大小边界。
- `read_file`: 文本 codec 与有界读取/错误码。
