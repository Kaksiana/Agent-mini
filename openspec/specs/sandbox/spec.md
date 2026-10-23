# sandbox Specification

## Purpose
定义文件沙箱与 read_file 契约：四步路径校验、root/大小/扩展名限制、TOCTOU 边界、结构化读取错误。

## Requirements

### Requirement: 沙箱四步校验

`Sandbox.resolve(rel_path)` MUST 拒绝绝对路径/POSIX/Windows 盘符、空/`.`、`..`、隐藏文件、非白名单扩展名、超长路径；拼接 root 后 MUST `resolve()` 并确认仍在 root 下；失败抛 `SandboxViolation(error_code)`。

#### Scenario: 上级目录

- **WHEN** 解析 `../../etc/passwd`
- **THEN** 抛 SandboxViolation(path_escape)

#### Scenario: 符号链接逃逸

- **WHEN** root 内符号链接指向外部
- **THEN** 抛 SandboxViolation(path_escape)

### Requirement: read_file

read_file MUST 从 ToolContext 取 root，不接受模型参数 root；读取前校验大小与二进制，空文件返回空 content + 元信息；返回 JSON content/size/encoding；错误均 ToolResult。

#### Scenario: 超限文件

- **WHEN** 文件超过 max_file_size
- **THEN** file_too_large

#### Scenario: 二进制

- **WHEN** 文件含 NUL
- **THEN** binary_file
