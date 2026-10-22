# S02「模型接入：错误处理与重试」产出评估报告

> 评估日期：2026-10-22  
> 基准提交：`eda077a`（`main`，与 `origin/main` 一致）  
> 评估性质：独立只读代码评估；除本报告与 Prompt 记录外，不修改实现、测试、Issue、PLAN 或 OpenSpec  
> 总体结论：**有条件通过；处理 P1 后方可进入 S03**

## 1. 评估范围与基准

### 1.1 实际读取内容

| 类别 | 路径与章节 |
| --- | --- |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` 的错误、重试、测试与日志条款 |
| 阶段范围 | `Docs/PLAN.md` S01、S02、S03、进度记录 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-LLM-03，并抽查 FR-LLM-01/02/04/05 边界 |
| 设计契约 | `Docs/DESIGN.md` §1.1、§1.3、§3.1、§3.7、§4、§6、§7、§8 |
| 测试定义 | `Docs/TESTING.md` TDD 规则、TC-L2-004/005/006、S02 覆盖边界与准出标准 |
| 过程记录 | `Docs/PROMPT.md` Prompt 26；`Docs/ISSUE.md` ISSUE-024/025 与 S02 阶段问题记录；`MEMORY.md`、`README.md` |
| 实现与测试 | `agent_mini/llm/client.py`、`errors.py`、`models.py`；`tests/contract/test_llm_retry.py`、`test_llm_timeout.py`、`test_llm_http_errors.py`；`pyproject.toml` |
| OpenSpec | `openspec/specs/llm-client/spec.md`；归档 change `2026-10-22-s02-llm-error-retry` |
| 流程证据 | 提交 `dce5d24`、`6ebbe24`、`efa14a4`、`4407e7a`、`eda077a` 及实现前后树 |

### 1.2 基准间的一致性与缺口

1. PLAN、DESIGN、TESTING 与 `llm-client` 主规格对默认行为基本一致：400、401/403、429、5xx、超时和连接错误分类明确；仅 429/5xx 重试；默认共 3 次请求。
2. `llm-client` 主规格要求“最多 3 次总请求”，实现公开的 `RetryPolicy.max_attempts` 却只校验大于等于 1，允许任意更大值，存在直接契约冲突。
3. OpenSpec 全局工程规范要求所有可预期异常继承 `AgentError`，`llm-client` 主规格和 ISSUE-024 又允许 S02–S19 使用临时 `LLMError` 根。严格校验只能验证格式，不能消除两份规格的语义冲突。
4. TESTING 的 TC-L2-005 要求“桩延迟超过 timeout、不无限等待”；实际测试直接抛 `httpx.ReadTimeout`，只验证异常转换，没有验证配置的 timeout 真正控制等待上限。
5. 全局工程规范要求重试记录 `attempt`；实现只有局部循环变量，没有日志、事件或可观察记录出口。

## 2. 复核命令与结果

| 命令/检查 | 关键结果 | 结论 |
| --- | --- | --- |
| `git status -sb` | `main...origin/main`，无工作区变更 | 通过 |
| S02 三个契约文件 | `8 passed` | 通过 |
| `python -m pytest -q` | `58 passed` | 通过 |
| 覆盖率门禁 | 总覆盖率 `93.84%`，要求 80% | 通过 |
| `pytest -q -m contract` | `50 passed, 8 deselected in 25.02s` | 功能通过；不满足 TESTING 声明的 L2 `< 3s` |
| `ruff check .` | `All checks passed!` | 通过 |
| `ruff format --check .` | `49 files already formatted` | 通过 |
| `mypy agent_mini` | 34 个源文件无错误 | 通过 |
| `openspec validate --all --strict` | `3 passed, 0 failed` | 结构校验通过；仍存在规格语义冲突 |
| `python -m pip check` | `No broken requirements found` | 通过 |
| wheel 构建与仓库外导入 | wheel 成功；可导入 `HttpLLMClient`、`RetryPolicy`、`LLMTimeoutError` | 通过 |
| wheel 内容抽查 | 包含 `agent_mini/llm/*.py` 与 `systemdb/schema.sql` | 通过 |
| 实现前红灯重建 | 从 `efa14a4^` 导出实现、叠加 `efa14a4` 的 3 个新测试文件：8 failed | TDD 红因有效，不是收集错误 |
| 定向重试探针 | `max_attempts=4` 时实际 4 次请求 | 不符合“最多 3 次” |
| 定向退避探针 | 达到 8 秒上限后可出现 `8.1 → 8.0` | 可配置高尝试次数下不再单调 |
| 定向状态探针 | HTTP 302 被映射为 `LLMBadRequestError` | 未分类状态映射过宽 |

### 2.1 未复跑项目

- 未调用真实 DeepSeek API：真实限流和超时行为按计划留待 S18；本次不产生外部费用。
- 未重新执行 `pip install -e ".[dev]"`：Prompt 26 已记录干净 venv 结果；本次以 `pip check`、wheel 隔离安装和仓库外导入复核依赖/打包。
- 未执行长时间真实网络超时：测试必须保持离线；本报告据测试结构判断 TC-L2-005 的等待上限未被有效断言。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与阶段范围 | 有条件通过 | 错误分类与重试均在 S02 范围内，无 Runtime/Tool/Memory 越界；可配置尝试次数突破 3 次契约 |
| HTTP/httpx 错误分类 | 有条件通过 | 400、401/403、429、5xx、超时、连接错误正确；其他 3xx/非预期状态统一落到 BadRequest |
| 重试正确性 | 不通过 | 默认 3 次路径正确，但公开策略允许超过硬上限；达到退避 cap 后单调性不成立 |
| 超时边界 | 有条件通过 | 代码把 timeout 交给 httpx 且不重试；现有测试不能证明等待上限生效 |
| 异常模型 | 有条件通过 | 类型、code、http_status 基本正确；临时根与 OpenSpec 全局 `AgentError` MUST 条款冲突 |
| 测试质量/TDD | 有条件通过 | 8 个红灯可重建且当前全绿；超时、协议错误不重试、http_status 和策略上界覆盖不足 |
| 可观测性 | 不通过 | 重试没有记录 attempt，违反全局 OpenSpec 强制条款 |
| 代码质量 | 通过 | Ruff、格式、mypy 通过；函数长度、嵌套、命名和异步 sleep 合理，无 noqa/type-ignore |
| 安全性 | 通过 | 错误消息未携带密钥/响应体；无真实 API 调用；无禁用 Agent 框架依赖 |
| 性能与有界性 | 有条件通过 | 默认尝试次数有界且使用异步 sleep；公共策略可放大请求，L2 契约集耗时超文档目标 |
| 打包与依赖 | 通过 | 无新增依赖，wheel 与隔离导入成功，既有依赖健康 |
| 流程与文档 | 有条件通过 | 文档/OpenSpec 先于实现，测试与实现同提交，最后归档；子包说明过时且规格存在冲突 |

## 4. 问题清单

### P0

无。

### P1

#### S02-P1-01：公开重试策略可突破“最多 3 次总请求”

- **位置**：`agent_mini/llm/client.py:40-45`、`:73-79`、`:95-108`，符号 `RetryPolicy`、`HttpLLMClient.chat`
- **问题描述**：`max_attempts` 只验证不小于 1，没有最大值。定向探针设置为 4 后确实发出 4 次 500 请求。该行为还使 8 秒退避上限生效后，随机抖动可能令相邻延迟下降，和文档“单调递增”声明冲突。
- **判定依据**：`openspec/specs/llm-client/spec.md:114-126`、`Docs/DESIGN.md:156` 明确要求最多 3 次总请求；FR-LLM-03 要求有界退避。
- **建议方向**：明确“配置值”与“安全硬上限”的关系；若规格维持最多 3 次，在策略构造处限制 1–3 并增加 0、负数、4、非整数测试；若确需更大值，先修改规格并保证 cap 后延迟不下降。

#### S02-P1-02：重试没有记录 attempt

- **位置**：`agent_mini/llm/client.py:95-108`，符号 `HttpLLMClient.chat`
- **问题描述**：实现计算了 `attempt`，但没有日志、事件、回调或结果字段记录。后续无法区分一次 LLM 步骤中的多个 HTTP attempt，也无法按规范审计重试放大。
- **判定依据**：`openspec/specs/engineering-standards/spec.md:770-775` 明确要求重试必须记录 `attempt`；DESIGN 的 trace 规则区分 LLM step 与内部 attempt。
- **建议方向**：在不引入 Runtime step 的前提下提供结构化 `llm.retry` 记录或可注入事件出口，字段至少包含 attempt、最大尝试次数、状态类别和等待时长；不得记录密钥或完整响应体。

#### S02-P1-03：TC-L2-005 没有验证 timeout 控制真实等待上限

- **位置**：`tests/contract/test_llm_timeout.py:19-43`
- **问题描述**：respx 直接抛 `ReadTimeout`，无论客户端是否把 `ModelConfig.timeout` 传给 httpx，该测试都能通过。它验证的是异常分类、请求次数和错误消息，不是“桩延迟超过 timeout 后及时终止”。
- **判定依据**：`Docs/TESTING.md:133` 要求延迟超过 timeout 且不无限等待；PLAN S02 验收标准要求超时不挂起；全局规范禁止测试自证。
- **建议方向**：引入可控时钟/传输替身或直接断言底层客户端 timeout 配置，并设置独立的测试级上限；保证删除 `timeout=config.timeout` 后测试会失败。

#### S02-P1-04：OpenSpec 对异常根存在互相冲突的 MUST 条款

- **位置**：`openspec/specs/engineering-standards/spec.md:722-730`；`openspec/specs/llm-client/spec.md:105-107`；`Docs/ISSUE.md:276-286`
- **问题描述**：全局规格要求所有可预期失败映射为 `AgentError` 子类，llm-client 规格却要求暂时继承独立 `LLMError`。ISSUE-024 的阶段决策合理解释了原因，但没有在全局规格中形成显式阶段例外。`openspec validate --strict` 不会检测这种语义矛盾。
- **判定依据**：AGENT 文档优先与 OpenSpec 全局规范；准出标准要求规范与实现一致。
- **建议方向**：在全局规格中明确 S20 前的临时例外和到期条件，或提前落最小 `AgentError`；不能同时保留两个无条件 MUST。

### P2

#### S02-P2-01：未分类 HTTP 状态被误报为 BadRequest

- **位置**：`agent_mini/llm/client.py:179-183`，符号 `_client_error`
- **问题描述**：除 401/403 外的所有非成功、非重试状态都返回 `LLMBadRequestError`，定向探针显示 302 也被归类为 `LLM_BAD_REQUEST`。这会掩盖代理重定向、协议异常或未知状态。
- **判定依据**：DESIGN 和 OpenSpec 只明确 400、401/403、429、5xx；外部响应应按不可信边界显式分类。
- **建议方向**：限制 BadRequest 到明确 4xx 集合或所有非 429 的 4xx，并为 3xx/非法状态设置协议或连接类错误；补充状态矩阵测试。

#### S02-P2-02：RetryPolicy 的运行时类型校验不完整

- **位置**：`agent_mini/llm/client.py:40-45`、`:73-79`
- **问题描述**：公共 dataclass 依赖静态注解，布尔值、浮点数或不可调用 sleep 可延迟到 `range()`/调用时才以原生异常失败。
- **判定依据**：公共配置边界应在构造处失败并给出稳定可读错误；S21 会把该策略接入配置层。
- **建议方向**：在策略模型中集中验证整数范围和 sleep callable，或迁移为受约束的 Pydantic 配置模型。

#### S02-P2-03：llm 子包说明仍声称 S02 未实现

- **位置**：`agent_mini/llm/__init__.py:1`
- **问题描述**：模块 docstring 仍为“错误分类与重试待 S02”，与 PLAN、README、MEMORY 的 S02 已完成状态冲突。
- **判定依据**：AGENT 文档同步与全局注释真实性要求。
- **建议方向**：更新为 S01/S02 已落地的当前职责，避免阶段状态写入长期易过期的说明。

#### S02-P2-04：L2 契约测试耗时超出测试文档目标

- **位置**：`Docs/TESTING.md:77-84`；S02 三个测试文件的客户端构造方式
- **问题描述**：文档目标为 L2 `< 3s`，本机 `pytest -m contract` 为 25.02 秒；仅 S02 的 8 个测试为约 10.6 秒。各用例主要耗时在默认 httpx 客户端初始化/调用，而非断言逻辑。
- **判定依据**：TESTING 测试分层的运行时间目标；快速契约测试有助于 TDD 反馈。
- **建议方向**：复用或注入轻量 MockTransport/客户端工厂，避免每例构造真实默认传输；若 3 秒目标不再现实，应基于 CI 数据修订文档。

#### S02-P2-05：错误类型测试未直接断言具体类与 http_status

- **位置**：`tests/contract/test_llm_retry.py:69-96`、`test_llm_timeout.py:37-43`、`test_llm_http_errors.py:37-77`
- **问题描述**：测试主要捕获宽泛 `LLMError`，再比较类名字符串和 code；没有断言各异常的 `http_status`，也没有 HTTP 成功但协议错误时“只请求一次”的客户端级测试。
- **判定依据**：主规格要求稳定类型、code/http_status；测试应直接验证公共契约并能捕获错误继承/映射回归。
- **建议方向**：直接使用具体异常类作为 `pytest.raises` 目标，参数化 code/http_status，并增加协议错误不重试的 route call_count 断言。

### Info

#### S02-INFO-01：TDD 红灯证据可独立重建

- 在临时目录以 `efa14a4^` 的实现配合 `efa14a4` 的新测试运行，8 个测试全部进入执行阶段失败；红因分别是原始 HTTPStatusError、未转换 ReadTimeout/ConnectError 和缺少状态分类，符合 TDD 规则。

#### S02-INFO-02：未发现阶段越界或新增依赖

- 变更仅涉及 `llm/client.py`、`llm/errors.py` 及 L2 契约测试；未引入 Runtime、Tool、Memory、配置加载、接口层或禁用 Agent 框架；`pyproject.toml` 无 S02 新依赖。

#### S02-INFO-03：默认重试和错误分类主路径正确

- 默认 429→500→200 共请求 3 次，两次等待落在 0.5–0.6、1.0–1.1 秒区间；重试耗尽、4xx、超时和连接错误均能映射到稳定 LLMError 子类，未暴露原始响应或密钥。

## 5. 需求—实现—测试追溯

| 需求/TC | 实现位置 | 测试位置 | 覆盖结论 |
| --- | --- | --- | --- |
| FR-LLM-03 | `HttpLLMClient.chat`、`_is_retryable`、`_backoff_delay`、错误类型 | 三个 S02 契约测试文件 | 默认路径覆盖；策略上界和 attempt 记录缺失 |
| TC-L2-004 | `client.py:95-108,160-177` | `test_llm_retry.py` | 429/500/200、耗尽分类、等待区间已覆盖；大于 3 的策略未拒绝，cap 后单调性未覆盖 |
| TC-L2-005 | `client.py:80-85,96-101` | `test_llm_timeout.py` | ReadTimeout 转换、单请求、消息秒数已覆盖；真实 timeout 上限未覆盖 |
| TC-L2-006 | `client.py:100-109,179-183` | `test_llm_http_errors.py` | 400/401/403、连接错误和不重试已覆盖；其他状态及 http_status 未覆盖 |

## 6. 边界抽查

- **是否只重试 429/5xx：**默认实现是；4xx、超时、连接错误、成功响应后的协议错误不会进入重试分支。
- **是否最多 3 次：**默认是，但公共策略可配置为 4 或更高，故整体契约不成立。
- **退避是否单调：**默认两次等待必然单调；达到 8 秒 cap 后不保证。
- **是否使用阻塞 sleep：**否，默认使用 `asyncio.sleep`。
- **是否越界到 Runtime/Tool/Memory：**否。
- **是否记录 attempt：**否。
- **是否使用真实 API：**本次评估没有；S02 产出本身保留 S18 live 边界。
- **是否泄露密钥或响应正文：**未发现。

## 7. 技术债与后续阶段影响

| 阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S03/S04 | 重试 attempt 不可观察，可能被误当成新的模型步骤或无法计入 trace | Runtime 开始累计步骤/usage/错误 | 进入 S03 前提供内部 attempt 事件或明确接口 |
| S03+ | 调用方设置大于 3 的尝试次数造成请求放大 | Runtime/配置层开始注入 RetryPolicy | 进入 S03 前限制上界或修订规格 |
| S18 | timeout 测试没有证明真实网络等待上限 | live 环境出现慢连接/半开连接 | S18 前补强离线 timeout 契约与有限 live 验收 |
| S18 | 3xx/未知状态误分类为 BadRequest | 代理、网关或 base_url 重定向 | live 验收前补状态矩阵 |
| S20 | 临时 LLMError 根与全局规范冲突 | 统一异常映射和 HTTP 接口落地 | 按 ISSUE-024 迁移；当前先补全局规格例外 |
| S21 | RetryPolicy 类型/范围未形成配置模型 | retry 从配置文件或环境变量加载 | S21 合并到受约束配置模型 |

另有既存前置债务：S01 的 TC-L2-007 尚缺“thinking 开启且 tools 非空”的组合回归测试。本问题不由 S02 引入，但在 S03/S04 开始消费消息协议前仍应补齐。

## 8. 总体结论

S02 默认业务路径、错误类型、退避计算、TDD 过程、打包与静态质量总体可靠，现有测试全部通过；但“最多 3 次”、attempt 可观测性、timeout 非自证测试和 OpenSpec 异常根语义冲突均属于进入 Runtime 阶段前应消除的 P1。

**结论：暂不建议进入 S03。**

进入 S03 前必须处理：

1. S02-P1-01：限制或重新规范最大尝试次数，并修正 cap 后单调性契约。
2. S02-P1-02：为内部重试提供不泄密的 attempt 记录。
3. S02-P1-03：补充能验证实际 timeout 配置/等待上限的测试。
4. S02-P1-04：消除 OpenSpec 全局异常根与 llm-client 临时根的无条件 MUST 冲突。

P2 可登记后进入后续阶段，但建议同步修复过时子包说明和状态矩阵测试。

## 9. 工作区状态与副作用

### 9.1 状态

- 评估开始前：`git status --short` 无输出，`main` 与 `origin/main` 一致。
- 评估命令结束后、归档报告前：被跟踪文件仍无变化。
- 按 `AGENT.md` 归档规则，本次新增 `Docs/S02-report.md` 并向 `Docs/PROMPT.md` 追加本轮记录；未修改实现、测试、Issue、PLAN、OpenSpec 或远程状态。

### 9.2 副作用

- pytest/coverage 可能刷新被忽略的 `.pytest_cache/`、`.coverage`、`__pycache__/`。
- wheel 构建可能刷新被忽略的 `agent_mini.egg-info/`。
- 仓库外 TDD 红灯重建目录：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s02-red-fb93b2f0adce49519d81fc48757a69c1`。
- 仓库外 wheel/安装目录：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s02-wheel-383ce17733634cb0810f8f9699e12612`。
- 上述产物均未被 Git 跟踪；需要时由人工确认后清理。

