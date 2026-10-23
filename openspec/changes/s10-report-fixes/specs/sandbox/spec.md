## ADDED Requirements

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
