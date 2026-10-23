# write-file Specification

## Purpose
定义 write_file 契约：沙箱复用、默认不覆盖、同目录临时文件+fsync+replace、失败清理与往返一致。

## Requirements

### Requirement: 沙箱写入与覆盖保护

write_file MUST 复用 Sandbox.resolve；父目录不存在 MUST parent_not_found；目标存在且 overwrite=false MUST file_exists 且不落盘/无临时残留；overwrite=true 才替换。

#### Scenario: 默认不覆盖

- **WHEN** 目标已存在且 overwrite=false
- **THEN** file_exists，目标内容不变，无临时文件

#### Scenario: 显式覆盖

- **WHEN** overwrite=true
- **THEN** 目标内容更新

### Requirement: 原子写与清理

写入 MUST 在目标同目录创建临时文件，fsync 后 os.replace；校验/编码/超限失败 MUST 在临时文件创建前返回；写入或替换失败 MUST 清理临时文件且不留下部分目标。

#### Scenario: 替换失败

- **WHEN** os.replace 抛 OSError
- **THEN** file_write_error，无目标/临时残留

### Requirement: 内容与编码

空内容 MUST 写空文件；内容字节数超过 max_file_size MUST file_too_large 且不落盘；编码 MUST 仅文本 codec；写入后 read_file MUST 往返一致（保留换行）。

#### Scenario: 往返

- **WHEN** 写入 "a\nb\n" 后 read_file
- **THEN** 内容一致

### Requirement: 原子不覆盖与父目录竞态

write_file MUST 在临时文件创建后与发布前验证 parent/temp 仍在沙箱 root 内；overwrite=false MUST 使用同目录原子 link 发布，EEXIST MUST file_exists；overwrite=true 才 replace。

#### Scenario: 并发创建

- **WHEN** exists 检查后竞争者创建目标
- **THEN** file_exists，竞争者内容不被覆盖，无临时残留

#### Scenario: 父目录替换

- **WHEN** 临时文件落到 root 外
- **THEN** path_escape，外部无目标/临时残留

### Requirement: 目录句柄锁定发布

write_file MUST 在 root→target parent 的目录句柄锁定期间完成临时文件创建与 link/replace；Windows MUST 不共享 DELETE 并校验最终路径与 reparse 属性；失败 MUST 只清理锁定目录内临时文件，MUST NOT 对重新解析的 target 做补偿删除。

#### Scenario: 父目录 junction

- **WHEN** 发布前父目录被替换为 root 外 junction
- **THEN** path_escape，外部文件不被删除/覆盖
