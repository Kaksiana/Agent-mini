## ADDED Requirements

### Requirement: 请求绑定与 Memory 边界

`RegistryExecutor.bind_request` MUST 保留 sandbox_root/max_file_size；Memory MUST 原子 pipeline 写、校验 max_rounds/ttl/session、坏轮次逐条跳过、写回超时可注入；Agent MUST 为三种安全阀保存最终 assistant 与元数据。

#### Scenario: 沙箱字段保留

- **WHEN** bind_request 更新 session/trace
- **THEN** sandbox_root/max_file_size 不变

#### Scenario: 坏轮次

- **WHEN** 一条记录损坏
- **THEN** 仅跳过该轮，其他轮仍返回
