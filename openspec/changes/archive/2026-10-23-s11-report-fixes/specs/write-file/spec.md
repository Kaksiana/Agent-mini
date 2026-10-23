## ADDED Requirements

### Requirement: 原子不覆盖与父目录竞态

write_file MUST 在临时文件创建后与发布前验证 parent/temp 仍在沙箱 root 内；overwrite=false MUST 使用同目录原子 link 发布，EEXIST MUST file_exists；overwrite=true 才 replace。

#### Scenario: 并发创建

- **WHEN** exists 检查后竞争者创建目标
- **THEN** file_exists，竞争者内容不被覆盖，无临时残留

#### Scenario: 父目录替换

- **WHEN** 临时文件落到 root 外
- **THEN** path_escape，外部无目标/临时残留
