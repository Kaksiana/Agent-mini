# S08 独立评估报告

> 评估日期：2026-10-23  
> 基准提交：`b72c784`（`main` 与 `origin/main` 一致）  
> 评估性质：只读代码、测试、规范、流程与分发复核  
> 总体结论：**不通过；修复 6 项 P1 后方可进入 S09**（修复后见 §10；S08 已恢复准入）

## 1. 评估范围与基准

### 1.1 实际读取范围

| 基准 | 实际读取位置 | 核对重点 |
| --- | --- | --- |
| 阶段计划与 DoD | `Docs/PLAN.md` S08、§4、§5、阶段状态表 | S08 输出、验收、前置阶段与准出状态 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-TOOL-03、NFR-COMPAT-01、UC-03 | 默认/指定 IANA 时区和 Windows/Linux 兼容性 |
| 设计契约 | `Docs/DESIGN.md` §1.1/1.3、§2.2、§3.3、§6～§8 | ZoneInfo、默认时区、别名、错误码、依赖与风险 |
| 测试定义 | `Docs/TESTING.md` TC-L1-004/005、§2、§4.2.8、§5、§6.2 | 确定性、默认/UTC/非法时区与准出标准 |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、Issue、OpenSpec、依赖、提交与门禁 |
| 前置修复 | `Docs/S07-report.md` §10；提交 `2a6fbe7`、`ebd0946` | S07 P1 是否按流程闭环后再进入 S08 |
| 过程记录 | `Docs/PROMPT.md` S08；`Docs/ISSUE.md` ISSUE-034；`MEMORY.md` S08；README | Prompt 原文、红绿摘要、问题时序与完成声明 |
| OpenSpec | `openspec/changes/archive/2026-10-23-s08-tool-time/`；`openspec/specs/time-tool/spec.md` | change 时序、参数、错误、注入和归档 |
| 实现与测试 | `agent_mini/tools/builtin/time_tool.py`；`agent_mini/tools/registry.py`；`tests/unit/test_time_tool.py`；骨架测试 | 时区解析、Schema、真实 Registry 路径和断言质量 |
| 构建与依赖 | `pyproject.toml`、wheel、临时 venv | tzdata 声明、包文件、Windows 仓库外运行 |

### 1.2 文档基准之间的一致性与缺口

- `PLAN`、FR-TOOL-03 与 TC-L1-004/005 对默认时区、指定 IANA 时区和非法时区的主要求一致。
- S08 Prompt 要求 Schema 字段为 `timezone`，TC-L1-005 使用 `tz`。归档 design 选择“Schema 只公开 timezone、handler 直调兼容 tz”，方向已记录，但 Schema 根描述仍含 `tz`，模型可见却无法调用。
- time-tool 主规格要求非字符串返回 `invalid_timezone`；实际 Registry 会先由 pydantic 返回 `invalid_arguments`，现有非字符串测试只直调 handler。
- time-tool 主规格要求固定 `now_provider` 的输出可被确定性断言；测试注入了固定时间，却只断言偏移和时区名，没有断言固定时间值或完整 ISO8601。
- `REQUIREMENT` NFR-COMPAT-01 声明 Linux/Windows 均可运行；Windows 全新 venv 无系统 IANA 数据且 wheel 未声明 `tzdata`，默认和 UTC 均失败。
- `PLAN`、README、MEMORY、ISSUE 已声明 S08 完成，但上述功能、测试、依赖与流程缺口尚未反映。

## 2. 复核命令与结果

### 2.1 实际复跑

| 命令/验证 | 关键结果 |
| --- | --- |
| `git status --short --branch`、`git rev-parse HEAD/origin/main` | 评估前工作区干净；本地与远端均为 `b72c784` |
| `git log/show/diff ebd0946..b72c784` | S08 OpenSpec `330b5a5` 先于代码 `c0c68e9`；代码/测试同 commit；文档 `63f1c22`、归档 `b72c784` 随后完成 |
| `python -m pytest -q -m unit -p no:cacheprovider` | **109 passed，64 deselected，0.55s** |
| `python -m pytest -q -m contract -p no:cacheprovider` | **64 passed，109 deselected，44.78s** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing`（coverage 在仓库外） | **173 passed，45.61s；总覆盖率 96%（文档精确值 95.94%）；time_tool 100%** |
| `ruff format --check .`、`ruff check .` | **58 files already formatted；All checks passed** |
| `mypy agent_mini tests` | **Success: no issues found in 55 source files** |
| `openspec validate --all --strict` | **7 passed，0 failed**；无活动 change |
| `python -m pip check` | 当前开发环境 **No broken requirements found** |
| 禁用框架、`noqa`、`type: ignore`、skip、pytz/dateutil 扫描 | S08 实现与测试零命中；只使用标准库 API |
| `git diff ebd0946..HEAD -- pyproject.toml` | 无差异；没有声明任何 S08 运行依赖 |

### 2.2 定向行为探针

| 探针 | 实际结果 | 判定 |
| --- | --- | --- |
| 直调 `current_time(tz=123)` | `invalid_timezone` | handler 符合文档 |
| Registry 执行 `{"timezone": 123}` | `invalid_arguments` | **真实工具路径违反 time-tool 错误码契约** |
| Registry 执行 `{"timezone": ""/"utc"/"Mars/Base"}` | 均 `invalid_timezone` | 字符串非法值路径正确 |
| Registry 执行 `{"tz": "UTC"}` | `invalid_arguments` | tz 只是直调别名，不是工具协议字段 |
| 序列化 TimeArgs JSON Schema | properties 只有 timezone，但根 description 含 `tz` 文本 | **模型可见描述暴露会被 Registry 拒绝的别名** |
| 当前开发环境 | `tzdata` 已全局安装，`ZoneInfo` 可用 | 解释现有测试全绿 |
| 全新 Windows venv 安装 wheel | `tzdata_spec=None`、`TZPATH=()`；默认与 UTC 均返回 `invalid_timezone` | **分发后核心功能不可用** |
| 在同一临时 venv 手工安装 tzdata | 默认 Asia/Shanghai 与 UTC 立即成功 | 根因确认为未声明时区数据库依赖 |

### 2.3 wheel 与仓库外验证

- `python -m pip wheel . --no-deps` 成功；wheel 包含 `time_tool.py`、`calculator.py` 与 `systemdb/schema.sql`。
- 全新 venv 依据 wheel 元数据只安装 httpx、pydantic 及其传递依赖；`pip check` 仍显示无缺失，因为 tzdata 根本未写入元数据。
- wheel 可导入，但 time 的默认与 UTC 行为均失败；因此“可导入”不能作为 S08 分发可用的证据。
- 手工补装 `tzdata 2026.5` 后同一 wheel 无需改代码即可正常返回，排除了实现主路径以外的原因。

### 2.4 TDD 与历史流程复核

- 父提交中 time 模块和测试均不存在；最终实现与测试在 `c0c68e9` 同一提交。Prompt 完整保存，记录 9 个用例先红后绿，但未提交工作区的原始红灯无法从 Git 独立重建。
- S08 OpenSpec change 先于 S08 代码并已严格校验、归档，S08 自身 Docs First 主时序正确。
- ISSUE-034 在 `c0c68e9` 的父提交中计数为 0，却被该代码提交 footer 引用；直到后续 `63f1c22` 才写入 ISSUE。
- S07 报告修复 `2a6fbe7` 在 calculator change 已归档后直接改变行为；其前后没有新的 OpenSpec change 或登记例外，不满足 S08 的流程前置闭环。

### 2.5 未复跑项

- 未调用真实 LLM、HTTP、数据库或外部搜索；均不属于 S08。
- 未实现或运行 S09～S12 的 todo/沙箱/文件/search。
- 未运行 Linux 容器；本次已在项目明确支持且当前实际使用的 Windows 上完成隔离 venv 复现。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | 不通过 | 未越界实现后续工具，但 NFR-COMPAT-01 的 Windows 全新环境不可用。 |
| 默认/指定时区正确性 | 不通过 | 已装 tzdata 时 Asia/Shanghai/UTC 正确；按 wheel 元数据安装时两者均失败。 |
| 参数与错误边界 | 不通过 | 字符串非法值正确；非字符串在 handler/Registry 分别返回 invalid_timezone/invalid_arguments。 |
| 输出与时间注入 | 有条件通过 | 实现会使用 now_provider 并正确转换 aware/naive；测试没有证明固定瞬间进入输出，naive 分支也未单独断言。 |
| 注册与 Schema | 不通过 | timezone 字段与正常 Registry 路径可用；Schema 描述泄漏无效 tz 别名，tz 实际被 Registry 拒绝。 |
| 测试质量与 TDD | 不通过 | 173 个测试全绿、覆盖率上升，但未覆盖干净 Windows、真实非字符串 Registry 语义和固定时间值。 |
| 全局代码规范 | 有条件通过 | Ruff、format、mypy、函数长度、嵌套、中文 docstring 均通过；Issue/OpenSpec/commit 流程仍有违规。 |
| 打包与分发 | 不通过 | wheel 文件完整且可导入，但缺少时区数据库元数据，核心工具在全新 Windows 安装不可用。 |
| 依赖审计 | 不通过 | 未引入禁用框架或第三方时区逻辑库；但运行所需 tzdata 未声明，pip check 无法发现。 |
| 流程与文档闭环 | 不通过 | S08 change 顺序正确；ISSUE-034 后补，S07 归档后修复绕过 change，完成文档又未披露分发失败。 |
| 可复现性 | 不通过 | 开发机依赖全局 tzdata；干净 venv 复现失败，属于环境依赖泄漏。 |
| 后续阶段影响 | 不通过 | S12/M2、S18 真实工具调用和 S21 配置化都会继承时区数据与参数协议缺陷。 |

## 4. 问题清单

### P0

无。未发现数据破坏、任意代码执行、密钥泄露或进程级安全问题。

### P1

#### S08-P1-01 — Windows wheel 安装缺少时区数据库，time 核心功能不可用

- **位置**：`pyproject.toml:11-24`；`agent_mini/tools/builtin/time_tool.py:11,37-45`；`Docs/REQUIREMENT.md:272`
- **问题描述**：项目声明 Windows/Linux 均可运行，但 wheel 未声明 tzdata。全新 Windows venv 的 `TZPATH=()` 且没有 tzdata，默认 Asia/Shanghai 和显式 UTC 都被判为 `invalid_timezone`。开发机测试依赖全局已安装的 tzdata，形成隐藏环境依赖。
- **判定依据**：NFR-COMPAT-01；工程规范依赖条款要求运行依赖统一声明于 `[project].dependencies`；阶段 DoD 要求 wheel 分发后可用，而不只是可导入。
- **建议方向**：先以 OpenSpec/设计澄清标准库 zoneinfo 的数据来源，再声明受支持平台所需的 tzdata（可使用恰当的平台标记与版本范围）；新增无系统时区库的 Windows 隔离安装验收，并验证默认、UTC、DST 区域。

#### S08-P1-02 — 非字符串时区在真实 Registry 路径返回错误错误码

- **位置**：`agent_mini/tools/builtin/time_tool.py:16-19,27-40`，`TimeArgs/current_time`；`agent_mini/tools/registry.py:125-130`；`tests/unit/test_time_tool.py:34-39`
- **问题描述**：测试用 `current_time(tz=123)` 绕过 pydantic，因此得到 `invalid_timezone`；模型真实调用 `{"timezone": 123}` 会先返回通用 `invalid_arguments`。主规格与 TESTING 均宣称非字符串为 invalid_timezone，文档、直调和真实工具协议三者不一致。
- **判定依据**：time-tool 主规格“非法时区”；`Docs/TESTING.md:215`；工程规范 CR-08 要求稳定错误码和边界正确。
- **建议方向**：明确类型校验属于 Registry 通用错误还是 time 领域错误，并统一规格与实现；若保留 invalid_timezone，需让真实 Registry 路径保持该码并补 bool/list/int 参数化测试，不能只直调 handler。

#### S08-P1-03 — 模型 Schema 描述暴露了实际会被拒绝的 `tz` 别名

- **位置**：`agent_mini/tools/builtin/time_tool.py:16-19`，`TimeArgs` docstring；`tests/unit/test_time_tool.py:52-59`；归档 design“参数”决策
- **问题描述**：pydantic 将 TimeArgs docstring 写入 parameters 根 description，因此发送给模型的完整 Schema 含“tz 兼容别名”；但 properties 没有 tz，Registry 也会把 tz 判为 `invalid_arguments`。现有测试只检查 properties，漏掉模型实际看到的完整 Schema。
- **判定依据**：归档 design 与 ISSUE-034 都要求 tz 不公开到 Schema；FR-TOOL-01 要求合法、无误导的 JSON Schema；工程规范要求外部协议字段与实现一致。
- **建议方向**：从模型可见的 Schema 文本中移除直调专用别名，或把别名正式建模并让 Registry 接受；对完整序列化 Schema 断言不存在未支持参数提示。

#### S08-P1-04 — 固定时钟测试没有断言固定时间，无法证明注入生效

- **位置**：`tests/unit/test_time_tool.py:11-31`，`FIXED_UTC/_fixed/test_default_timezone_is_shanghai/test_tz_keyword_uses_utc`
- **问题描述**：测试注入 2026-01-01，但只断言 `+08:00`/`+00:00` 和时区名。保留 now_provider 参数却完全忽略其返回值、改用系统当前时间，测试仍会通过；也没有解析或精确断言 ISO8601 时间戳。
- **判定依据**：time-tool 主规格“确定性时间注入”；S08 Prompt 要求确定性断言；`Docs/TESTING.md:25` 禁止依赖系统时间并要求注入 Clock/固定时区。
- **建议方向**：精确断言默认时区与 UTC 的完整固定输出或解析后比较固定瞬间、offset 和 zone；增加 naive provider 与 aware provider 转换用例。

#### S08-P1-05 — ISSUE-034 在实现后补记，代码提交引用了尚不存在的问题

- **位置**：提交 `c0c68e9`、`63f1c22`；`Docs/ISSUE.md:420-429`
- **问题描述**：`c0c68e9` 已实现 timezone/tz 冲突方案并写 `Refs: ISSUE-034`，但其父提交中 ISSUE-034 不存在；问题直到下一文档提交才登记。OpenSpec 提前描述了冲突，仍不能替代 AGENT 指定的 ISSUE 先记账流程。
- **判定依据**：`AGENT.md` §4.1 要求阻塞/缺陷/踩坑“先记录再修复”；§4 验证要求修复提交可反查到已存在的问题记录。
- **建议方向**：不改写历史；在后续流程修复记录中如实登记时序偏差和防复发措施。以后先提交 ISSUE/OpenSpec 决策，再提交实现，并保证 footer 引用可在父提交解析。

#### S08-P1-06 — S07 报告修复在归档后绕过 OpenSpec change

- **位置**：提交 `1d6d93b`、`2a6fbe7`、`ebd0946`；`Docs/S07-report.md` §10；`Docs/PLAN.md:314`
- **问题描述**：calculator change 在 `1d6d93b` 已归档，随后 `2a6fbe7` 修改参数 Schema 边界和错误行为，却没有新建修复 change，也没有登记例外；S08 在该不完整流程闭环之上启动。
- **判定依据**：`AGENT.md` §6.1 禁止绕过 change 直接改行为；`Docs/PLAN.md` §5.1 明确归档后阶段内变更必须新建 change 或记录例外；工程规范要求行为变更走 OpenSpec。
- **建议方向**：不修改归档历史；创建追补 change/流程审计记录，确认 calculator 主规格与修复行为一致并登记历史偏差，之后再恢复前置阶段准入。

### P2

#### S08-P2-01 — feat 提交正文超过 72 字符

- **位置**：提交 `c0c68e9` 的 commit body
- **问题描述**：正文单行长度为 119 字符，超过项目规定的 72 字符；subject 与提交拆分本身合规。
- **判定依据**：`AGENT.md` §5.2 第 2 条。
- **建议方向**：后续提交在 72 字符内换行；不为纯格式问题重写已推送历史。

#### S08-P2-02 — naive now_provider 分支没有行为测试

- **位置**：`agent_mini/tools/builtin/time_tool.py:43-44`；`tests/unit/test_time_tool.py:11-49`
- **问题描述**：design 明确“naive 时补 tzinfo、aware 时 astimezone”，现有 `_fixed` 总是返回 aware datetime。行覆盖率 100% 不等于两个条件分支都被验证。
- **判定依据**：工程规范测试要求覆盖分支、边界与异常路径；归档 design“时间注入”决策。
- **建议方向**：补 naive datetime 的明确语义测试，并保留 aware UTC 到目标时区的转换测试。

#### S08-P2-03 — builtin 包说明仍过期且默认注册依赖隐式导入

- **位置**：`agent_mini/tools/__init__.py:1`；`agent_mini/tools/builtin/__init__.py:1`；`time_tool.py:22-26`
- **问题描述**：包 docstring 仍写待 S06/S06–S12 落地；新进程只导入 DEFAULT_REGISTRY 时 Schema 为空，必须显式导入具体模块触发装饰器。S07 已记录该债务，S08 继续扩大依赖导入顺序的工具集合。
- **判定依据**：工程规范 CR-04/CR-15；M2 要求六工具最终注册可用。
- **建议方向**：更新过期说明；最迟 S12/M2 收口时建立显式 builtin 加载入口，并在 fresh process 断言完整工具集合。

### Info

#### S08-INFO-01 — 已有时区转换主逻辑简洁且无越界依赖

- **位置**：`agent_mini/tools/builtin/time_tool.py:27-45`
- **观察**：默认常量集中；ZoneInfo 异常结构化；timezone 优先级明确；aware datetime 使用 astimezone；没有引入 pytz/dateutil、网络、配置容器或后续工具。
- **建议**：修复数据依赖和协议边界时保留当前单职责结构。

#### S08-INFO-02 — S08 OpenSpec 与累计自动门禁本身通过

- **位置**：提交 `330b5a5`～`b72c784`；本次复跑结果
- **观察**：S08 change 先于实现、代码与测试同 commit、归档 strict validate 通过；173 个测试、Ruff、mypy 和覆盖率门禁均通过，且覆盖率高于 S07 修复后的 95.81%。
- **建议**：增加干净环境和完整协议断言，避免本机全绿掩盖分发缺陷。

## 5. 需求—实现—测试追溯

| 需求/TC | 实现位置 | 测试位置 | 覆盖结论 | 是否越界 |
| --- | --- | --- | --- | --- |
| FR-TOOL-03：默认 IANA 时区 | `DEFAULT_TIMEZONE/current_time` | `test_default_timezone_is_shanghai` | **部分**；开发机通过，干净 Windows wheel 失败，固定时间未断言 | 否 |
| FR-TOOL-03：指定 IANA 时区 | `ZoneInfo(name)` | `test_tz_keyword_uses_utc`、`test_registry_timezone_path` | **部分**；UTC 在开发机通过，分发环境失败；TC 的 tz 仅直调 | 否 |
| FR-TOOL-03：非法时区 | `current_time` 错误分支 | `test_invalid_timezone_is_structured` | 字符串非法值覆盖；非字符串真实 Registry 码不符 | 否 |
| NFR-COMPAT-01：Windows/Linux | zoneinfo 数据依赖未声明 | 无干净平台测试 | **未覆盖且 Windows 失败** | 否 |
| TC-L1-004：默认 +08:00、ISO8601 | default 分支 | `test_default_timezone_is_shanghai` | 偏移/名称覆盖；时间戳格式与固定瞬间未有效断言 | 否；配置化留 S21 |
| TC-L1-005：UTC/非法 | tz 直调、timezone Registry | invalid 参数化、Registry 正例 | **部分**；双参数方言分离，非字符串 Registry 不符合 | 否 |
| OpenSpec：确定性 now_provider | `current_time(now_provider=...)` | `_fixed` 被传入两个测试 | 注入调用被覆盖，但返回值语义未被断言 | 否 |
| 注册与 Schema | `TimeArgs/@tool` | Schema/Registry 两个测试 | properties 覆盖；完整 Schema 描述泄漏 tz | S07 模式延续，不越界 |
| S00 骨架回填 | `time_tool.py` 新模块 | `test_package_skeleton.py` | 增加期望条目；无 skip、无删除既有条目 | 否 |

## 6. 边界抽查

- **是否越界实现 todo、沙箱、文件、search、Memory、HTTP、配置或真实 API：否。**
- **是否新增 pytz/dateutil 或其他时区逻辑库：否。** 但缺少 Windows 所需的 IANA 数据包声明。
- **默认时区来源是否明确：是。** `DEFAULT_TIMEZONE="Asia/Shanghai"`，S21 再配置化。
- **真实 Registry 是否接受 TC 写法 tz：否。** 仅 handler 直调接受，Registry 因额外字段返回 invalid_arguments。
- **完整模型 Schema 是否完全隐藏 tz：否。** properties 隐藏，但根 description 含别名提示。
- **非字符串是否稳定返回 invalid_timezone：否。** 直调是，Registry 是 invalid_arguments。
- **固定 now_provider 是否得到确定性验证：否。** 测试未断言 2026-01-01 时间值。
- **wheel 是否包含模块/package-data：是。** 但依赖元数据不足导致 Windows 运行失败。
- **S00 占位测试如何处理：增加 time_tool 期望条目；未跳过、未删除既有条目。**
- **是否出现重试、退避、HTTP 分类或网络调用：否。**

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险/技术债 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S09 todo | Registry 通用校验与领域错误码边界尚未统一 | todo 字段类型错误需要领域码 | S09 开工前修 P1-02，形成统一规则 |
| S10/S11 | 干净平台依赖未纳入验收会再次漏检系统能力 | 文件/符号链接行为跨 Windows/Linux | S10 前把平台隔离测试纳入验收 |
| S12/M2 | builtin 依赖隐式 import，time 又依赖外部时区数据 | 六工具 fresh process 装配 | M2 收口前建立显式加载和 clean-install 演示 |
| S18 | 模型看到 tz 提示却调用会被拒绝；部署机可能没有 tzdata | 真实模型自主调用 time | S09 前修 P1-01/02/03，S18 做真实闭环 |
| S21 | 默认时区将配置化，但数据源仍缺失 | 用户配置任意 IANA 名称 | S21 只接管配置，不应延后 tzdata 修复 |
| 流程治理 | 归档后修复和 Issue 后补会削弱审计链 | 后续报告修复继续直接提交代码 | S09 前完成 P1-05/06 的流程纠偏 |

## 8. 总体结论

### 8.1 是否可以进入 S09

**暂不可进入 S09。** time 在当前已安装 tzdata 的开发环境中实现简洁、主样例正确，累计 173 个测试及静态/OpenSpec 门禁均通过；但 wheel 按声明依赖安装后在 Windows 无法解析任何 IANA 时区，真实 Registry 的非字符串错误码与规格不一致，Schema 又向模型暴露无效别名，确定性时钟测试不足，并存在 Issue/OpenSpec 流程违规。

进入 S09 前必须处理：

1. S08-P1-01：声明并验证跨平台 IANA 时区数据来源，保证 clean-install 可运行。
2. S08-P1-02：统一非字符串时区在 Registry 与 handler 的错误语义。
3. S08-P1-03：消除模型 Schema 中会被 Registry 拒绝的 tz 提示。
4. S08-P1-04：精确断言固定时间和 ISO8601 输出，证明 now_provider 真正生效。
5. S08-P1-05：如实登记 ISSUE-034 后补的历史流程偏差和防复发措施。
6. S08-P1-06：用追补 change/例外记录闭合 S07 归档后行为修复流程。

可选建议：补 naive provider 分支测试、规范后续 commit body 行宽、在 M2 前建立 builtin 显式加载入口。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short --branch` 仅输出 `## main...origin/main`。
- 测试、探针、wheel 与隔离 venv 完成后且报告写入前：仍仅输出 `## main...origin/main`。
- 本轮按全局评估规则新增 `Docs/S08-report.md`，并在 `Docs/PROMPT.md` 追加本轮原始 Prompt；未修改实现、测试、OpenSpec、PLAN、ISSUE、README、MEMORY 或远程状态。

### 9.2 评估副作用

- coverage 文件：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s08.coverage`、`agent-mini-s08-final-verify.coverage`。
- wheel：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s08-wheel-84ca2f7a57f743b498cde5d7085fd47d`。
- 隔离 venv：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s08-venv-8548d2c845c9440e8470a4cc49abb1a9`；先验证无 tzdata 的失败，再手工安装 tzdata 2026.5 完成因果复验。
- 最终独立复验 venv：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s08-final-venv-2e24aa5e713a4e58b1048d4cd0b89a67`；保持无 tzdata，再次复现默认 time 失败。
- `agent-mini-s08-final` 与 `agent-mini-s08-target` 的时间戳早于本次评估，属于既有 S08 产物，未计为本轮创建。
- wheel/测试可能刷新被忽略的 `.coverage`、`.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、`agent_mini.egg-info/` 与 `__pycache__/`；评估前未记录 ignored 基线，无法区分既有与刷新项。
- 上述临时/忽略产物未自动删除；如需清理，请人工确认路径后处理。非忽略工作区变更仅应为本报告与 Prompt 记录。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S08-P1-01 Windows 缺 tzdata | `pyproject.toml` 声明 `tzdata>=2025.1; platform_system == "Windows"` | wheel METADATA 含该 Requires-Dist；干净 venv 安装后默认/UTC 均成功 |
| S08-P1-02 非字符串 Registry | `TimeArgs` before validator 将非字符串转为字符串，handler 统一 `invalid_timezone` | Registry `{"timezone":123}` 测试 |
| S08-P1-03 Schema 暴露 tz | TimeArgs docstring 移除 tz；完整 Schema 断言无 `tz`/别名 | `test_schema_description_does_not_expose_tz` |
| S08-P1-04 固定时钟未断言 | 精确断言完整 ISO 字符串；补 naive provider | 默认 `08:00:00+08:00`、UTC `00:00:00+00:00`、naive 测试 |
| S08-P1-05 ISSUE-034 后补 | 历史无法回改；新 change 记录流程例外，后续先记账 | `s07-s08-report-fixes` |
| S08-P1-06 S07 归档后绕过 change | 新建 `s07-s08-report-fixes`，追溯 calculator Registry 超长边界 | 归档 change |
| 分发验证 | 全新 Windows venv 安装 wheel；`current_time` 默认/UTC 成功 | 安装/运行退出码 0 |

**复验**：176 passed；unit 112、contract 64；覆盖率 95.97%；mypy 55 files 0 errors；ruff/format/OpenSpec/wheel 通过。S08 可进入 S09。
