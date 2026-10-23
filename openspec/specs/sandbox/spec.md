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

### Requirement: Windows 路径与设备名

Sandbox MUST 使用 POSIX/Windows 分隔符拆段；任意 `..` MUST path_escape；反斜杠隐藏段 MUST hidden_path；Windows 保留设备名 MUST invalid_path。

#### Scenario: 反斜杠隐藏

- **WHEN** 解析 `dir\.hidden.txt`
- **THEN** hidden_path

#### Scenario: 任意上级

- **WHEN** 解析 `a/../b.txt`
- **THEN** path_escape

#### Scenario: 设备名

- **WHEN** 解析 `NUL.txt`
- **THEN** invalid_path

### Requirement: 有界读取

read_file MUST 最多读取 limit+1 字节；stat 后文件增长至超限 MUST file_too_large；其他 OSError MUST file_read_error。

#### Scenario: 增长

- **WHEN** stat 报告小文件但实际内容超过 limit
- **THEN** file_too_large
