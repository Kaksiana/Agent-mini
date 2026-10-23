# S10 代码产出独立评估报告

> 评估时间：2026-10-23 14:10（Asia/Shanghai）  
> 基准提交：`2d8ee5d`（`main` 与 `origin/main` 一致）  
> 评估方式：只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态  
> 修复状态：见 §10；S10 已恢复准入

## 1. 评估范围与基准

| 类别 | 实际读取范围 | 评估基准 |
| --- | --- | --- |
| 阶段计划 | `Docs/PLAN.md:160-180,339-350` | S10 交付沙箱内核与 read_file；S11 写文件不在本阶段 |
| 功能需求 | `Docs/REQUIREMENT.md:188-199,257-273,279-297` | FR-TOOL-05、FR-TOOL-07、NFR-SEC-01、NFR-COMPAT-01、AC-04/16 |
| 设计契约 | `Docs/DESIGN.md:300-318` 及 §8 风险 | 四步校验、可信 root/limit、编码/大小/二进制、TOCTOU 边界 |
| 测试定义 | `Docs/TESTING.md:92-105,228-236,274-283` | TC-L1-010/011/012、TC-L5-003 及 S10 覆盖边界 |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、安全、skip、目录、错误、提交、OpenSpec |
| 过程记录 | `Docs/PROMPT.md:1701-1757`、`Docs/ISSUE.md:441-457`、`MEMORY.md:3-15`、`README.md:1-3` | S09 前置修复、S10 红绿/验收/风险声明 |
| 实现与测试 | `agent_mini/tools/sandbox.py`、`agent_mini/tools/builtin/read_file.py`、`agent_mini/tools/registry.py`、`tests/unit/test_sandbox_readfile.py` | Windows/POSIX 路径、真实 Registry、文件读取与错误行为 |
| OpenSpec | `openspec/specs/sandbox/spec.md`、归档 change `2026-10-23-s10-tool-sandbox-readfile` | 主规格、归档任务与最终树一致性 |
| 提交历史 | `f71568f`、`a278271`、`f74cc68`、`5a1164f`、`2d8ee5d` | change 先行、实现/测试同提交、归档以及归档后补测 |

### 1.1 基准间的一致性与缺口

- PLAN、REQUIREMENT、DESIGN 与 OpenSpec 对“可信 root、绝对路径/越界/符号链接阻断、read_file 大小与编码限制”总体一致。
- 主规格要求 `Sandbox.resolve()` 拒绝 `..`，实现只拒绝最终越界的 `..`；`sub/../safe.txt` 会被接受。REQUIREMENT/PLAN 更接近“阻断 `..` 逃逸”，因此规格自身存在“全部拒绝”和“仅拒绝逃逸”两种口径。
- DESIGN 把大小上限写入 Sandbox 第四步，但主规格/change design 把大小检查放在 read_file；当前 `Sandbox.max_file_size` 只保存不使用。
- TESTING 顶部称 L3–L5 尚未执行，S10 覆盖边界却把 TC-L5-003 标为已覆盖；实际安全用例全部标记为 unit。
- `Docs/TESTING.md:12` 写自动化测试 214，但同格明细为 unit 151 + contract 64，且下一行和实际执行均为 215。

## 2. 复核命令与结果

| 命令/探针 | 关键结果 | 判定 |
| --- | --- | --- |
| `git status --short --branch`、`git rev-parse HEAD/origin/main` | 评估前为 `## main...origin/main`；两者均为 `2d8ee5d` | 通过 |
| `git log/show/diff 640bd89..2d8ee5d` | 规划 → 代码+测试 → 文档 → 归档 → 归档后补 junction chain 测试 | 流程失败 |
| `python -m pytest -m unit -q` | 151 passed，64 deselected | 通过 |
| `python -m pytest -m contract -q` | 单独复跑 64 passed，151 deselected，45.48s | 通过 |
| 全量覆盖率命令 | 215 passed；总覆盖率 96.66%；sandbox/read_file 均 100% | 通过 |
| `python -m ruff check .` / `ruff format --check .` | All checks passed；62 files formatted | 通过 |
| `python -m mypy agent_mini tests` | 59 source files，0 errors | 通过 |
| `openspec validate --all --strict` | 9 passed，0 failed；仅工程规范长 Requirement Info | 通过 |
| `python -m pip check` | No broken requirements found | 通过 |
| wheel → 全新 venv → 仓库外 Registry read_file | 安装、导入、读取均成功；wheel 含 sandbox/read_file/schema.sql | 通过 |
| 可信上下文伪造探针 | 模型参数携带 sandbox_root/max_file_size/session_id 均 `invalid_arguments`；Schema properties 仅 path/encoding | 通过 |
| Windows 隐藏路径探针 | `sub\.secret.txt` 被 Sandbox 接受 | **失败** |
| `..` 规范探针 | `sub/../safe.txt` 被接受 | 与主规格 MUST 冲突 |
| codec 探针 | base64/hex/rot_13 通过 lookup，decode 抛 LookupError；Registry 变成 `tool_execution_error`；空串静默回退 UTF-8 | **失败** |
| 文件增长探针 | stat 为 1B 后读取 2048B，在 1024B 限制下仍成功返回 size=2048 | **失败** |
| Windows 保留设备名探针 | `NUL.txt`/`CON.txt`/`COM1.txt` 等被 Sandbox 接受；当前 read_file 在 stat 阶段返回 file_not_found | S11 风险 |
| skip/xfail 扫描 | symlink 与 chain 用例各含一个 `pytest.skip` 分支 | **违反全局规范** |
| `git diff --check 640bd89..2d8ee5d` | 5 个文档新增 EOF 空行 | P2 |
| BOM 探针 | 归档后提交给 ISSUE/PLAN/PROMPT/TESTING/MEMORY 引入 UTF-8 BOM | P2 |

本次已复跑 unit、contract、全量覆盖率、Ruff、format、mypy、OpenSpec、wheel、隔离安装、仓库外执行与定向安全探针。未复跑 Linux 容器/CI、真实 HTTP、真实模型；TC-L1-012 的写分支按 PLAN 留 S11，TC-L4-002 留 S18。

## 3. 维度结论表

| 维度 | 结论 | 一句话理由 | 证据位置 |
| --- | --- | --- | --- |
| 需求与范围合规 | 有条件通过 | 未越界实现 write_file/search/Runtime；但隐藏/编码/大小约束未完全满足，限制常量也未全部落地 | PLAN S10；S10-P1-01～03；S10-P2-01 |
| 路径与沙箱安全 | 不通过 | 基本逃逸阻断有效，但 Windows 反斜杠隐藏段绕过策略，主规格要求的任意 `..` 拒绝也未实现 | `sandbox.py:37-55`；S10-P1-01 |
| read_file 契约 | 不通过 | 正常/空/静态超限/二进制路径有效；非文本 codec 和 stat 后增长破坏编码/大小契约 | `read_file.py:33-73`；S10-P1-02/03 |
| 可信上下文与 Schema | 通过 | root/limit/session 不在模型字段，伪造参数被 Registry 在 handler 前拒绝 | `registry.py:30-37,115-173`；Schema/伪造探针 |
| 错误边界 | 不通过 | codec 的 LookupError 未被领域层捕获，真实 Registry 退化为通用 tool_execution_error | `read_file.py:41-71`；S10-P1-02 |
| 测试质量与 TDD | 不通过 | 215 个测试全绿且新增代码 100%，但真实 Registry、codec/增长/Windows 分隔符缺测，并提交了 skip | `test_sandbox_readfile.py`；S10-P1-01～04 |
| 全局代码规范 | 有条件通过 | Ruff/format/mypy 与复杂度通过；skip、测试目录、commit body、BOM/空行仍违规 | S10-P1-04；S10-P2-03/04 |
| 打包与分发 | 通过 | wheel 含新增模块和 schema.sql，全新 venv 可安装并仓库外执行 | 本报告 §2 |
| 依赖审计 | 有条件通过 | S10 无新增运行依赖、无禁框架；但 DESIGN/TESTING 宣称的 hypothesis 未声明或使用 | `pyproject.toml`；S10-P2-03 |
| 流程与文档闭环 | 不通过 | OpenSpec 先于实现，但必需 chain 用例在归档后补交，旧 Prompt 摘要被直接改写，测试计数也矛盾 | 提交 `5a1164f`、`2d8ee5d`；S10-P1-04/05 |
| 可复现性 | 通过 | 当前 Windows 环境和全新 wheel venv 均可复现门禁；Linux 本次未复跑 | 本报告 §2 |
| 后续阶段影响 | 不通过 | S11 直接复用 Sandbox，现有 Windows 路径策略、设备名和 TOCTOU/大小边界会进入写路径 | 本报告 §7 |

## 4. 问题清单

### P0

无。非竞态条件下，定向 `../` 越界、POSIX/Windows 绝对路径和符号链接/junction 指向外部均会被阻断。已声明的 TOCTOU 残余风险单列为技术债，不把项目明确接受的 S10 最小防护重复定为 P0。

### P1

#### S10-P1-01 — Windows 隐藏路径策略可被反斜杠绕过，`..` 行为也与主规格不一致

- **位置**：`agent_mini/tools/sandbox.py:37-55`；`openspec/specs/sandbox/spec.md:8-20`；`tests/unit/test_sandbox_readfile.py:27-52`
- **问题描述**：隐藏段只用 `PurePosixPath.parts` 检查。在 Windows 上，`sub\.secret.txt` 被当成真实子路径并接受；测试只覆盖根级 `.secret.txt`。另外 `sub/../safe.txt` 被规范化为 root 内路径后接受，而主规格写明 `Sandbox.resolve` 必须拒绝 `..`。
- **判定依据**：PLAN S10；FR-TOOL-07、NFR-SEC-01、AC-04；OpenSpec 沙箱四步校验；S10 Prompt 约束 5/12；NFR-COMPAT-01。
- **建议方向**：按 POSIX/Windows 两套分隔符规范化并检查每个原始 segment；先统一“拒绝全部 `..`”还是“仅拒绝逃逸”的规格，再增加正斜杠/反斜杠、根级/嵌套级组合测试。

#### S10-P1-02 — `codecs.lookup` 会放行非文本 codec，真实 Registry 返回错误错误码

- **位置**：`agent_mini/tools/builtin/read_file.py:41-45,55-73`；`tests/unit/test_sandbox_readfile.py:138-151`
- **问题描述**：base64、hex、rot_13 可通过 `codecs.lookup`，但 `bytes.decode` 随后抛未捕获 LookupError；直接 handler 抛异常，Registry 只返回通用 `tool_execution_error`，不是 `invalid_encoding`。空字符串又因 `encoding or DEFAULT_ENCODING` 被静默当作 UTF-8。
- **判定依据**：FR-TOOL-05；DESIGN §3.3 执行契约；S10 Prompt 约束 8/9 要求编码不支持与解码失败结构化且不得抛未捕获异常。
- **建议方向**：只接受文本编码并在 decode 边界捕获 LookupError/TypeError；明确空串策略；通过 `DEFAULT_REGISTRY.execute` 参数化断言领域错误码，避免只测 handler 直调。

#### S10-P1-03 — 文件可在 stat 后突破大小限制并被完整载入内存

- **位置**：`agent_mini/tools/builtin/read_file.py:55-73`；`Docs/DESIGN.md:307-308,316`
- **问题描述**：实现先 stat、再无上限 `read_bytes()`，读取后不复核长度。定向探针模拟文件在两步之间由 1B 增长到 2048B，1024B 上限下仍返回成功。除契约错误外，攻击者可让进程分配远大于 1 MiB 的内容。
- **判定依据**：PLAN S10“大小限制生效”；FR-TOOL-05；OpenSpec read_file Requirement；S10 Prompt 约束 5/8。TOCTOU 可声明残余风险，但不能把大小上限描述为已强制后仍无读取上界。
- **建议方向**：以 `limit + 1` 有界读取并按实际字节数判定，或至少在读取后再次拒绝超限；增加增长/替换回归测试并说明剩余父目录替换风险。

#### S10-P1-04 — 必需安全测试在归档后补交，且测试包含规范禁止的 skip

- **位置**：提交 `a278271`、`5a1164f`、`2d8ee5d`；归档 `tasks.md:1-18`；`tests/unit/test_sandbox_readfile.py:55-99`；`Docs/PROMPT.md:1729-1757`
- **问题描述**：原 Prompt 明确要求符号链接链且“缺少须登记 ISSUE”，但 chain 测试直到 OpenSpec 归档后才加入；没有新 change 或编号 ISSUE。归档 tasks 在当时已勾选全部安全测试/验收。两个 symlink 用例还保留 `pytest.skip` 分支，违反仓库禁止提交 skip 的硬规则。`2d8ee5d` 直接改写既有 Prompt 摘要计数，而不是追加纠偏记录。
- **判定依据**：`AGENT.md` §1/§2/§3/§4/§6.1；工程规范测试条款；S10 Prompt 约束 10～12、15/16。
- **建议方向**：用独立修复 change 承接本报告修复并如实记录归档后补测；平台能力不足时采用可执行替代或明确独立平台门禁，不提交 skip；历史摘要不再覆盖，追加纠偏条目。

#### S10-P1-05 — 测试状态与覆盖声明互相矛盾

- **位置**：`Docs/TESTING.md:9-14,228-236,274-283`；`Docs/PLAN.md:349`；`Docs/ISSUE.md:450-457`；`MEMORY.md:3-8`
- **问题描述**：TESTING 同时写“自动化 214（unit 151、contract 64）”和“215 passed”；顶部又称 L3–L5 未执行，覆盖边界却称 TC-L5-003 已覆盖，而测试实际统一标为 unit。文档还宣称隐藏路径与 `..` 均阻断，和定向探针不符。
- **判定依据**：`AGENT.md` §1/§7 要求文档、TC、实现和证据同步；阶段 DoD 禁止把部分覆盖标记为完整通过。
- **建议方向**：修正算术与状态；把 L5 安全套件拆成已运行的 unit 子断言和后续平台/竞态断言，或按 L5 正式执行并记录；修复行为后再恢复“全部阻断”声明。

### P2

#### S10-P2-01 — Sandbox 限制接口与设计声明不一致

- **位置**：`agent_mini/tools/sandbox.py:5-7,24-35,53-55`；`Docs/DESIGN.md:307`；S10 Prompt 约束 7
- **问题描述**：`Sandbox.max_file_size` 被保存但从未使用；“允许隐藏/允许空文件”也没有按 Prompt 提取为具名常量。Sandbox 的所谓第四步实际只检查扩展名，大小由 read_file 另行完成。
- **判定依据**：DESIGN 的 Sandbox 四步描述和原 Prompt 限制常量要求。
- **建议方向**：统一职责：要么给 Sandbox 明确的大小校验 API 并由读写工具复用，要么移除无效属性并把设计改为 read/write 各自执行大小策略；补齐显式策略常量。

#### S10-P2-02 — 所有文件系统读取错误均被误报为 `file_not_found`

- **位置**：`agent_mini/tools/builtin/read_file.py:55-65`；`tests/unit/test_sandbox_readfile.py:160-179`
- **问题描述**：权限错误、目录读取、瞬时 I/O 错误与真正不存在均映射为 `file_not_found`；测试甚至把人工 OSError 固化为该错误码，会误导模型采取“换路径”而非报告权限/I/O 问题。
- **判定依据**：DESIGN §3.3 要求稳定、可读、可定位的结构化错误；全局错误处理规范要求分类边界准确。
- **建议方向**：至少区分不存在与不可读/读取失败，保持外部消息不泄露绝对路径或系统细节。

#### S10-P2-03 — 文档指定 hypothesis 做沙箱属性测试，但项目未声明也未使用

- **位置**：`Docs/DESIGN.md:34,42`；`Docs/TESTING.md:313-324`；`pyproject.toml:17-25`
- **问题描述**：设计与测试工具表明确把 hypothesis 分配给沙箱组合路径，但依赖清单没有 hypothesis，测试也全是有限示例；Windows 分隔符缺陷正是组合覆盖缺失的结果之一。
- **判定依据**：依赖/测试文档必须与实际一致；TC-L5-003 属路径组合安全套件。
- **建议方向**：若保留选型则在 dev 依赖中锁定并增加受控属性测试；若不采用，先修改 DESIGN/TESTING，不能继续声称已使用。

#### S10-P2-04 — 提交与文档格式产生可避免的审计噪声

- **位置**：提交 `a278271`、`2d8ee5d`；`Docs/ISSUE.md`、`Docs/PLAN.md`、`Docs/PROMPT.md`、`Docs/TESTING.md`、`MEMORY.md`
- **问题描述**：feat commit body 单行 115 字符，超过 72；归档后测试提交给 5 个 Markdown 文件引入 BOM 和额外 EOF 空行；新增测试仍平铺在 `tests/unit/`。
- **判定依据**：`AGENT.md` §5.2；工程规范 D-03、目录与编码/可读性条款；`git diff --check`。
- **建议方向**：后续 body 换行，文档保持 UTF-8 无 BOM 与单个结尾换行；新测试迁到 `tests/unit/tools/` 镜像目录。不要为纯提交格式改写已推送历史。

### Info

#### S10-INFO-01 — TOCTOU 是已声明但必须在 S11 前重新审视的风险

- **位置**：`Docs/DESIGN.md:308`；归档 change design:11；`sandbox.py:50-55`、`read_file.py:49-63`
- **观察**：当前路径先 resolve 再 stat/open，父目录在两者之间被替换为 junction/symlink 时仍可能越界。S10 Prompt 明确允许最小防护，所以本报告不把已披露风险定为 P0；S11 写路径会把后果从读取扩大到写入。
- **建议**：S11 设计前确定威胁模型；若沙箱目录可能被不可信进程修改，应使用基于目录句柄/不跟随重解析点的打开方式，不能只复用字符串 realpath 检查。

#### S10-INFO-02 — Windows 保留设备名是 S11 的前置风险

- **位置**：`sandbox.py:37-55`；定向 `NUL.txt/CON.txt/COM1.txt` 探针
- **观察**：这些名称通过 Sandbox；当前 read_file 因 stat 失败而结构化返回，但未来 write_file 可能触发设备语义，而不是写入 root 中普通文件。
- **建议**：S11 开工前增加跨 Python 3.11+ 的 Windows 保留名拒绝规则和测试。

#### S10-INFO-03 — S09 前置 P1 已闭环

- **位置**：提交 `ab9f676` → `6615870` → `70c7073` → `640bd89`；`Docs/S09-report.md:219-233`
- **观察**：S09 报告修复使用独立 change 并在 S10 开工前归档；S09-P1-01～05 均有实现和测试证据，不构成 S10 前置阻塞。

## 5. 需求—实现—测试追溯表

| FR / TC | 实现位置 | 测试位置 | 覆盖 | 越界/缺口 |
| --- | --- | --- | --- | --- |
| FR-TOOL-05 | `read_file.py:21-73`；ToolContext root/limit | read_file 相关 11 个函数/参数用例 | 部分 | 非文本 codec、空编码、增长超限、真实 Registry 领域码缺失 |
| FR-TOOL-07 | `sandbox.py:16-58` | unsafe paths、symlink、junction chain | 部分 | Windows 反斜杠隐藏段；主规格 `..` 口径；设备名/TOCTOU 后续风险 |
| TC-L1-010 | resolve + containment | 参数化两种上级目录 | 是（定义内） | 未覆盖仍在 root 内的 `..`，与主规格冲突 |
| TC-L1-011 | POSIX/Windows absolute + realpath | absolute、symlink、junction chain | 是 | chain 在归档后补交；测试含 skip 分支 |
| TC-L1-012 | read_file 静态大小判断 | 2KB/1024B read | 部分 | write 分支正确留 S11；文件增长未覆盖 |
| TC-L5-003 | 多项路径策略 | 全部落在 unit 文件 | 部分 | 文档称 L5 未执行；缺 Windows 分隔符组合/设备名/属性测试/竞态 |
| TC-L4-002 | Agent/HTTP 自主工具闭环 | 未实现 | 否 | 正确留 S18 |

## 6. 边界抽查结论

- **是否越界实现 write_file/search/Memory/HTTP：否。** 只实现 Sandbox、read_file 与必要 ToolContext 字段。
- **`../`、绝对路径、外部 symlink/junction 是否阻断：典型逃逸路径是。** 但 root 内 `..` 被接受，与主规格字面要求冲突。
- **Windows 隐藏路径是否完整阻断：否。** 正斜杠/根级样例可阻断，反斜杠嵌套隐藏段可绕过。
- **可信 sandbox_root/max_file_size 是否能被模型覆盖：不能。** 伪造字段均在 Registry 白名单处返回 `invalid_arguments`。
- **大小上限是否对实际读取字节始终生效：否。** stat 后增长可成功返回超限数据。
- **编码错误是否始终得到领域错误码：否。** 非文本 codec 变成 `tool_execution_error`，空编码被静默接受。
- **TOCTOU 是否宣称强防护：否。** 文档如实声明未采用 O_NOFOLLOW 级原子性；这是已知边界。
- **符号链接链是否在归档前覆盖：否。** `2d8ee5d` 晚于归档 `5a1164f`。
- **S00 占位测试是否更新：是。** sandbox/read_file 已加入非占位清单和结构文件清单。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S11 | 反斜杠隐藏段与 Windows 设备名进入写路径 | 模型写 `dir\.hidden.txt` 或 `NUL.txt` | S11 开工前修 S10-P1-01，并补设备名规则 |
| S11 | Sandbox 大小属性无实际 API | write_file 试图复用 max_file_size | S11 design 先统一大小职责，避免复制校验 |
| S11 | resolve/open TOCTOU 可能把竞态扩大为越界写 | 沙箱目录可被其他进程修改 | S11 明确威胁模型；必要时升级原子打开策略 |
| S18 | read_file 非文本 codec 只给模型通用执行错误 | 模型选择 base64/hex/rot_13 | S11 前修领域错误，使模型可纠错 |
| S18 | 内置工具仍依赖显式导入才进入 DEFAULT_REGISTRY | 组合根未导入 read_file 模块 | S18/S21 建立显式 builtin 装载清单并测试六工具 |
| 跨平台 CI | 两个安全测试在能力不足时 skip | Linux/Windows runner 禁止 symlink/junction | 修复阶段建立不允许 skip 的平台矩阵和替代验证 |

## 8. 总体结论

**S10 暂不可进入 S11。** 基本 realpath containment、绝对路径、外部 symlink/junction、静态大小、二进制与正常文本读取均有效；215 个测试、覆盖率、静态检查、OpenSpec 和 wheel 门禁也通过。但 Windows 路径策略、编码判别、实际读取大小上限均存在可重复缺陷，必需的 chain 测试还在归档后补交并保留 skip。S11 会直接复用该安全边界，不能带着这些 P1 进入写文件阶段。

进入 S11 前必须处理：

1. **S10-P1-01**：统一 `..` 规格并修复 Windows 反斜杠隐藏段检查，补组合路径测试。
2. **S10-P1-02**：限制为文本 codec，统一空编码与 Registry 领域错误码。
3. **S10-P1-03**：对实际读取做有界/读取后大小校验，阻止 stat 后增长绕过。
4. **S10-P1-04**：用修复 change 闭合归档后补测流程，移除 skip，并追加而非覆盖过程记录。
5. **S10-P1-05**：修正测试总数、层级状态与“全部覆盖”声明。

可选建议：统一 Sandbox 大小职责；区分不可读与不存在；落实或删除 hypothesis 选型；S11 前拒绝 Windows 保留设备名。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked 改动；HEAD 与 `origin/main` 均为 `2d8ee5d`。
- **验证结束、报告落盘前**：tracked 工作区仍干净。
- **报告落盘后预期**：仅新增 `Docs/S10-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec 或远程状态，未提交、未推送。
- 测试/构建命令生成或更新被忽略的 `.coverage`、`.pytest_cache/`、`agent_mini.egg-info/` 与各级 `__pycache__/`；普通 `git status --short` 不显示。本次按评估边界未清理，需人工按需删除。
- 隔离安装目录保留于 `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s10-audit-4ec9c62db0c247f6a78bfc0aa6b074c1`，含 wheel、venv 与 fixture；需人工确认路径后清理。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S10-P1-01 Windows 隐藏/任意 `..` | 用 POSIX+Windows 拆段；任意 `..` 直接 path_escape；反斜杠隐藏/设备名拒绝 | 组合路径/设备名测试 |
| S10-P1-02 非文本 codec | 仅接受 `_is_text_encoding`；空编码 invalid_encoding | base64/hex/空编码测试 |
| S10-P1-03 stat 后增长 | 最多读 limit+1，超限 file_too_large | 小 stat + 大文件测试 |
| S10-P1-04 skip/归档后补测 | 移除 skip；Windows 用 junction，失败即测试失败；新 change 承接 | 32 个 S10 测试 |
| S10-P1-05 计数矛盾 | 按实际执行为 224 passed/unit 160/96.76% | 全量复跑 |
| S10-P2-01 限制接口 | Sandbox 保留 max_file_size/allowed_extensions；read_file 使用 | 测试 |
| S10-P2-02 错误码过粗 | FileNotFound → file_not_found；其他 OSError → file_read_error | stat/open 错误测试 |
| S10-P2-03 hypothesis | 仍未引入，登记为后续 | — |
| S10-P2-04 格式 | ruff/format 复核 | 全量静态检查 |

**复验**：224 passed；unit 160、contract 64；覆盖率 **96.76%**；mypy 59 files 0 errors；OpenSpec 10 passed；wheel/仓库外导入通过。S10 可进入 S11。

