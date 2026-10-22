## MODIFIED Requirements

### Requirement: S03 单轮直答接口

`Agent` MUST 通过构造器注入 `LLMClient`，并提供 `async def run(self, user_input: str) -> AgentResult`。无 `ToolExecutor` 的直答场景 MUST 只发送一条 `user` 消息、不传 tools、不接收 session_id；S04 有 executor 时同一入口进入工具循环；S05 在有 executor/无 executor 场景均应用 LoopPolicy。`truncated` 为累计结果字段，不属于 S03 排他禁止项。

#### Scenario: 正常直答

- **WHEN** 无 executor 的客户端返回无 tool_calls 的非空文本
- **THEN** Agent.run 只调用一次 chat，返回 steps=1、reply 为该文本

#### Scenario: 无工具路径

- **WHEN** 无 executor 的直答运行
- **THEN** 不执行工具，trace 为空、tool_calls=0、tool_traces 为空

#### Scenario: 空或纯空白内容

- **WHEN** 客户端返回 content=None、空字符串或纯空白且无 tool_calls
- **THEN** 抛 LLMEmptyResponseError

#### Scenario: 意外 tool_calls

- **WHEN** 无 executor 的客户端返回非空 tool_calls
- **THEN** 抛 LLMProtocolError，不执行工具

### Requirement: AgentResult 字段与不可变性

`AgentResult` MUST 是冻结模型，包含 reply、steps、usage、trace、tool_calls、tool_traces、truncated、termination_reason；usage 为所有 LLM 调用之和，reply 只表示最终文本（安全阀为固定文案），truncated 与 termination_reason 必须一致；额外字段 MUST 被拒绝。

#### Scenario: 字段完整性

- **WHEN** 循环正常结束或触发安全阀
- **THEN** 全部字段可读，truncated/termination_reason 语义正确，修改字段失败

#### Scenario: 正常收敛字段

- **WHEN** 循环正常结束
- **THEN** truncated=false、termination_reason=None，既有字段语义不变

## ADDED Requirements

### Requirement: Deadline 与重复检测硬化

deadline MUST 为有限正数，并从 Agent.run 开始计时；工具本地 TimeoutError MUST 归 tool_execution_error 而不是全局 deadline；LLM 调用超时 MUST 保留已尝试的 steps；重复签名 MUST 仅统计成功执行调用，invalid_arguments MUST NOT 与合法空对象碰撞。

#### Scenario: 工具本地超时

- **WHEN** executor 自身抛 TimeoutError 且全局 deadline 未到
- **THEN** tool trace 为 tool_execution_error，循环继续并可收敛，truncated=false

#### Scenario: 非法参数后合法空对象

- **WHEN** 连续非法参数后模型返回合法空对象 {}
- **THEN** 不误判 repeat，正常执行并最终收敛

#### Scenario: 非有限 deadline

- **WHEN** deadline_seconds 为 NaN/Infinity/布尔/非正数
- **THEN** LoopPolicy 构造失败，不进入循环

#### Scenario: LLM 超时步数

- **WHEN** 第二次 LLM 调用挂起超过 deadline
- **THEN** steps=2、truncated=true、reason=deadline
