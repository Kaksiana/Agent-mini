## Why

S11 报告发现父目录替换竞态、overwrite=false 并发覆盖、Windows 设备名不完整、TC-L4-002 错配与计数矛盾。S11 需闭环后进入 S12。

## What Changes

- 同目录临时文件创建后/发布前复核 root containment；失败 path_escape 并清理。
- overwrite=false 使用 os.link 原子发布，EEXIST→file_exists；overwrite=true 才 replace。
- 补全 COM1–COM9/LPT1–LPT9。
- 文件需求/PLAN 移除 TC-L4-002 错配；文件 E2E 留 S18。
- 统一测试计数；记录 Prompt 时序偏差。
