# S11 阶段代码产出独立评估报告

> 评估时间：2026-10-23 14:54（Asia/Shanghai）
> 基准提交：`d12eb65`（`main` 与 `origin/main` 一致）
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S11 暂不可进入 S12**  
> 修复状态：见 §10；S11 已恢复准入

## 1. 评估范围与基准

实际读取并交叉核对：

- `AGENT.md` §1–§10，重点是文档优先、TDD、Prompt 时机、Commit、OpenSpec、阶段 DoD 与评估报告归档。
- `Docs/PLAN.md` S10、S11、S12、§5 DoD 与阶段进度表。
- `Docs/REQUIREMENT.md` §5.3、UC-06、FR-TOOL-05/06/07、NFR-COMPAT-01、NFR-TEST-01。
- `Docs/DESIGN.md` §1.1/1.3、§2.2、§3.3、§4、§6、§7 ADR-006、§8、§9、变更记录 v0.25。
- `Docs/TESTING.md` TC-L1-010/011/012、TC-L4-002、TC-L5-003、S10/S11 覆盖边界、§5–§6。
- `Docs/PROMPT.md` S10 评估/修复与 S11 执行记录；`Docs/ISSUE.md` S10/S11 记录；`MEMORY.md` S10/S11 记录；`README.md` 安装、测试与阶段说明。
- `agent_mini/tools/sandbox.py`、`agent_mini/tools/builtin/read_file.py`、`agent_mini/tools/builtin/write_file.py`、`agent_mini/tools/registry.py`。
- `tests/unit/test_write_file.py`、`tests/unit/test_sandbox_readfile.py`、`tests/unit/test_package_skeleton.py`、`tests/unit/test_packaging_config.py`。
- `pyproject.toml`；`openspec/specs/write-file/spec.md`、`sandbox/spec.md`、`engineering-standards/spec.md`；归档 change `2026-10-23-s11-tool-writefile` 的 proposal/design/tasks/spec。
- S10 修复提交 `731b5e4`、`350b644`、`eb22379`、`6b2a44b`；S11 提交 `faa4f73`、`2efea20`、`13cdb66`、`d12eb65`。

基准文档存在三处直接不一致：

1. `PLAN`/`REQUIREMENT` 把文件读写映射到 TC-L4-002，但 `TESTING` 对 TC-L4-002 的完整定义是 calculator 的 HTTP 调用，不验证 read_file/write_file。
2. `TESTING.md:12` 写“自动化测试 214（unit 160、contract 64）”，算术结果应为 224，且同文件第 14 行及实跑结果已是 243（unit 179、contract 64）。
3. `PLAN`/FR/OpenSpec 主规格承诺默认不覆盖与沙箱内写入，change design 和 `DESIGN.md:308,317` 却接受非 CAS 与 resolve/open 竞态；定向探针证明该放宽会造成数据覆盖和沙箱外写入，不能视为无行为影响的设计说明。

## 2. 复核命令与结果

| 命令/检查 | 结果摘要 |
| --- | --- |
| `git status --short --branch`、`git rev-parse HEAD origin/main` | 评估前为干净的 `main...origin/main`；两者均为 `d12eb65` |
| `git log/show/diff --check` | OpenSpec 计划先于实现；实现与测试同 commit；S11 feat 正文单行 122 字符；文档提交新增 EOF 空行并给 README 引入 BOM |
| `pytest tests/unit/test_write_file.py -q` | **19 passed** |
| `pytest --cov=agent_mini --cov-report=term-missing -q` | **243 passed，97%**；write_file 模块 100% 行覆盖 |
| `pytest --collect-only -m unit/contract` | unit 179、contract 64；integration/e2e/slow/live 无已收集用例 |
| `ruff check agent_mini tests` | 通过，零告警 |
| `ruff format --check agent_mini tests` | 通过，61 files already formatted |
| `mypy agent_mini tests` | 通过，61 source files，0 errors |
| `openspec validate --all --strict` | **11 passed，0 failed**；engineering-standards 有既有 INFO 长度提示 |
| `pip wheel . --no-deps` | 成功生成 `agent_mini-0.1.0-py3-none-any.whl`；wheel 含 write_file 与 `systemdb/schema.sql` |
| Python 3.11.14 新 venv 安装 wheel + `[dev]`、仓库外导入/往返、`pip check` | 通过；wheel 外部导入位置正确，write→read 与 package-data 正常，无依赖冲突 |
| Python 3.11.14 新 venv 从仓库外以 `--import-mode=importlib` 跑全量 | **243 passed** |
| 默认不覆盖竞态探针 | 竞争者在 exists 检查后创建 `race.txt`；write_file 返回成功、`overwritten=false`，最终竞争者内容被替换 |
| 父目录 junction 竞态探针 | `resolve` 后把父目录换成指向 root 外的 junction；write_file 返回成功，root 外实际生成 `escaped.txt` |
| Windows 设备名探针 | `COM5.txt`、`COM9.txt`、`LPT4.txt`、`LPT9.txt` 均被 Sandbox 接受 |
| 非字符串直接调用探针 | 非字符串 path/encoding 均泄漏 `TypeError`；经 Registry 调用时会由 pydantic 拒绝 |

本次未复跑：

- TC-L4-002：HTTP 接口尚未实现，按计划留 S18；且该 TC 当前定义只覆盖 calculator，不能验收文件写入。
- TC-L5-003 独立层级命令与 LIVE：仓库未提供相应可执行测试；已有路径样例实际以 unit marker 运行。
- 真实 API：S11 不涉及模型调用，也未读取或使用任何真实密钥。

## 3. 维度结论表

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | **有条件通过** | diff 仅新增 write_file、测试与收口文档，未越界实现 search/Memory/HTTP/重试；但 FR-TOOL-06 的“不覆盖、沙箱内”在竞态下失效 |
| 沙箱与路径安全 | **不通过** | 静态 `..`/绝对路径/隐藏/外部 symlink 可阻断，但父目录 junction 竞态可真实写到 root 外；设备名集合也不完整 |
| 原子写与覆盖保护 | **不通过** | 同目录 mkstemp、文件 fsync、replace、失败清理在普通路径有效；exists+replace 使 `overwrite=false` 不是原子约束 |
| 内容、大小与编码 | **通过** | 先编码再按字节数限制；空内容、换行、未知/非文本 codec、不可编码内容均有测试，2KB/1KB 场景不落盘 |
| 错误边界与数据模型 | **有条件通过** | ToolResult 领域错误覆盖常规失败，严格 bool 生效；直接调用的 path/encoding 类型仍可抛 TypeError，Registry 路径未有 S11 专项测试 |
| 测试质量 | **不通过** | 19 个阶段用例和 100% 行覆盖有效，但未覆盖两项可复现安全竞态；权限保留、既有目标失败不变、Registry 注入也缺断言 |
| 全局规范符合性 | **不通过** | ruff/format/mypy 通过且无 noqa/type-ignore；但 P0 安全门禁、Prompt 记录时机和文档一致性不满足 AGENT/OpenSpec 规范 |
| 打包与分发 | **通过** | wheel 包含新增模块和 schema.sql；Python 3.11 隔离安装、仓库外导入、文件往返及 pip check 通过 |
| 依赖审计 | **通过** | S11 未改依赖；无禁用 Agent 框架、无未声明运行依赖；现有最新版解析在 Python 3.11 复现通过 |
| 流程与文档闭环 | **不通过** | change 先于实现、strict 校验和归档通过；但 Prompt 晚于代码提交，TC 映射/计数/完成声明互相矛盾 |
| 可复现性 | **通过** | 本机 Python 3.13 与全新 Python 3.11 wheel 环境均 243 passed；静态门禁、OpenSpec、wheel 均可复现 |
| 隐性风险与后续影响 | **不通过** | S18 并发 HTTP 请求会放大覆盖/越界竞态；S12/M2 仍缺明确 builtin 组合装载；崩溃持久性未 fsync 目录 |

## 4. 问题清单

### P0

#### S11-P0-01 — resolve 后父目录替换可造成真实沙箱外写入

- **位置**：`agent_mini/tools/sandbox.py:57-62`（`Sandbox.resolve`）；`agent_mini/tools/builtin/write_file.py:55-62,111-125`（`write_file` / `_atomic_write`）；`Docs/DESIGN.md:308,317`。
- **问题描述**：目标先解析并通过 containment，随后仅按字符串路径创建同目录临时文件和 replace。若这期间把目标父目录替换为指向 root 外的 junction，临时文件与最终文件都会落到 root 外。本次探针得到 `result_ok=True`、`outside_exists=True`，内容为待写数据。
- **判定依据**：FR-TOOL-06 要求“沙箱内写入”；FR-TOOL-07 要求符号链接逃逸阻断；`Docs/TESTING.md:388` 明确把沙箱越界定义为 P0；engineering-standards CR-14 和“安全类规则不得例外”。文档披露竞态不等于满足安全契约。
- **建议方向**：先明确可信目录威胁模型；对可被并发修改的沙箱使用基于已打开目录/文件句柄的 no-follow 或 Windows reparse-point 防护，并在最终提交前验证句柄对应路径仍在可信 root；增加真实 junction/symlink 交换回归测试。仅在字符串上二次 `resolve` 仍有新的竞态窗口。

#### S11-P0-02 — `overwrite=false` 在并发创建时仍覆盖数据

- **位置**：`agent_mini/tools/builtin/write_file.py:95-99,111-125`（`_prepare` / `_atomic_write`）；归档 change design:9-11；`Docs/DESIGN.md:317`。
- **问题描述**：`target.exists()` 与 `os.replace()` 分离。目标在检查后由另一请求创建时，本调用仍无条件 replace；探针显示函数返回成功且 `overwritten=false`，竞争者内容却已被覆盖。返回元数据也与实际副作用相反。
- **判定依据**：`Docs/PLAN.md:178` 要求默认不覆盖；FR-TOOL-06 是 P0 需求并明确“禁止覆盖”；OpenSpec 主规格要求 overwrite=false 时不落盘；`Docs/TESTING.md:388` 把数据损坏列为 P0。
- **建议方向**：把“不存在时发布”实现为 OS 级原子条件创建/链接，EEXIST 映射为 `file_exists`；只允许 `overwrite=true` 走 replace。补两个线程/进程同步到 exists 后的确定性测试，并使 `overwritten` 来自实际提交结果而非提交前快照。

### P1

#### S11-P1-01 — Windows 保留设备名规则不完整

- **位置**：`agent_mini/tools/sandbox.py:14-16,55-56`（`WINDOWS_RESERVED`）；`tests/unit/test_sandbox_readfile.py:27-55`；`Docs/DESIGN.md:307`；`Docs/S10-report.md` 修复记录。
- **问题描述**：集合只含 COM1–COM4、LPT1–LPT3；Windows 的 COM5–COM9、LPT4–LPT9（以及需统一考虑的设备名规范化变体）未覆盖。定向探针确认四个代表值均通过 resolve，与“Windows 保留设备名已拒绝”的设计/修复记录不符。
- **判定依据**：DESIGN §3.3 的沙箱步骤明确要求拒绝 Windows 保留设备名；AGENT §1/§7 要求文档、测试和实现一致；S11 直接复用该边界执行写操作。
- **建议方向**：按 Windows 规范集中生成完整集合并处理大小写、扩展名及规范化变体；补 COM9/LPT9 等边界测试，同时复核 read/write 均返回稳定 `invalid_path`。

#### S11-P1-02 — TC-L4-002 被错误用作文件读写验收项

- **位置**：`Docs/PLAN.md:179`；`Docs/REQUIREMENT.md:196-197`；`Docs/TESTING.md:243,272`。
- **问题描述**：PLAN/FR-TOOL-05/06 都引用 TC-L4-002，但该 TC 的前置、步骤和预期只描述 HTTP 触发 calculator 并得到 4；即使 S18 通过，也不能证明 read_file/write_file 可由 Agent/Registry 安全调用。
- **判定依据**：AGENT §1.3、§7.2 要求每条验收标准可映射到真实测试，编号可追溯；engineering-standards CR-02/CR-07/CR-15。
- **建议方向**：新增或重定义独立的文件读写 E2E TC，覆盖 write→read、默认不覆盖、越界/超限不落盘，并同步 REQUIREMENT/PLAN/TESTING；calculator 的 TC-L4-002 保持原语义。

#### S11-P1-03 — TESTING 的自动化数量与执行状态三方矛盾

- **位置**：`Docs/TESTING.md:9-14`；`Docs/PLAN.md:350`；`MEMORY.md:8`；`Docs/ISSUE.md:464`。
- **问题描述**：TESTING 第 12 行仍写 214 且括号为 160+64=224；第 14 行和其余收口文档写 243、179+64。本次实跑/收集均为 243、179+64。
- **判定依据**：AGENT §1、§8.6 与 TESTING §6.2 要求测试记录真实、文档与实现一致；阶段状态不能基于互相矛盾的门禁数字。
- **建议方向**：只保留一组由收集命令生成的当前统计；明确“设计 TC 数”和“pytest 参数化实例数”是不同口径，避免同表混写。

#### S11-P1-04 — S11 原始 Prompt 在实现与收口提交之后才入库

- **位置**：提交 `2efea20`、`13cdb66`、`d12eb65`；`Docs/PROMPT.md:1798-1811`。
- **问题描述**：实现提交和完成文档提交均未包含本轮 Prompt；原始 Prompt 到归档提交 `d12eb65` 才追加，无法满足“交互结束后、提交代码之前”的过程留痕。
- **判定依据**：AGENT §3“每轮交互结束后、提交代码之前”；§8 阶段收口五件套；Prompt 真实性属于审计链。
- **建议方向**：后续阶段先追加原始 Prompt/约束再提交实现；本阶段不要改写历史，可在修复 change/ISSUE 中如实记录过程偏差及整改方式。

### P2

#### S11-P2-01 — 多项已声明行为缺少直接测试

- **位置**：`tests/unit/test_write_file.py` 全文件；归档 change design:9-10；`Docs/DESIGN.md:317`。
- **问题描述**：未验证覆盖时权限保留、已有目标上的 replace 失败保持原内容、超限覆盖保持原内容、临时文件确在目标目录、fsync 被调用、Registry Schema/可信 context/伪造 sandbox_root 路径。100% 行覆盖没有验证这些语义。
- **判定依据**：AGENT §2 要求行为测试真实有效；OpenSpec/设计已把权限、fsync、失败清理和可信上下文写成契约。
- **建议方向**：用 spy/monkeypatch 与已有目标夹具补语义断言；至少增加一次 `DEFAULT_REGISTRY.execute("write_file", ...)` 和伪造可信字段拒绝测试。

#### S11-P2-02 — 直接 handler 的参数类型错误会泄漏 TypeError

- **位置**：`agent_mini/tools/builtin/write_file.py:70-84`（`_validate_options`）；`agent_mini/tools/sandbox.py:40-45`（`Sandbox.resolve`）；`tests/unit/test_write_file.py:145-170`。
- **问题描述**：代码特意为非字符串 content 和非 bool overwrite 返回领域错误，但非字符串 path/encoding 会分别从 pathlib/codecs 抛 TypeError。Registry 会由 pydantic 拦截，直接调用行为却不一致。
- **判定依据**：DESIGN §3.3 执行契约与 engineering-standards 错误处理规范要求工具失败转为 ToolResult；现有测试也把 handler 作为直接 API 使用。
- **建议方向**：统一入口边界：要么在 handler 显式校验 path/encoding 并结构化返回，要么只把 Registry 暴露为公共调用路径并让单测全部通过 Registry 验收。

#### S11-P2-03 — Commit 与 Markdown 格式产生审计噪声

- **位置**：提交 `2efea20` 正文；提交 `13cdb66`；`README.md`、`Docs/PLAN.md`、`Docs/TESTING.md`、`MEMORY.md`。
- **问题描述**：feat commit 正文单行 122 字符，超过 72；文档提交给多个文件增加多余 EOF 空行，并给 README 引入 UTF-8 BOM。`git show --check 13cdb66` 可复现 EOF 告警。
- **判定依据**：AGENT §5.2 正文每行 ≤72；engineering-standards 的编码、可读性与 CR-15。
- **建议方向**：后续提交正文换行；文档统一 UTF-8 无 BOM、单个结尾换行。不要为纯历史格式改写已推送 commit。

#### S11-P2-04 — 文档版本元数据和包 docstring 已过期

- **位置**：`Docs/DESIGN.md:6-9,536-540,567`；`agent_mini/tools/__init__.py:1`；`agent_mini/tools/builtin/__init__.py:1`。
- **问题描述**：DESIGN 变更记录已到 v0.25，但页首仍写 v0.13，§9 仍描述更早的模型/Runtime 修订；tools/builtin 包仍自称“占位/待 S06–S12 落地”，与 S06–S11 已完成不符。
- **判定依据**：AGENT §1 与 engineering-standards CR-04/CR-15 要求注释不过期、文档同步。
- **建议方向**：在独立文档修复中更新当前版本/本次修订范围，并把包 docstring 改为当前职责说明，不借机引入自动导入副作用。

### Info

#### S11-INFO-01 — 正常单请求路径实现质量良好

- **位置**：`write_file.py`、`test_write_file.py`、write-file 主规格。
- **观察**：字节级大小限制、严格 overwrite、文本 codec、空内容、换行、同目录临时文件、文件 fsync、权限 mode、replace 失败清理及 JSON 元信息实现清晰；ruff/mypy/行覆盖全绿。
- **建议**：保留现有分层和错误码，修复竞态时避免弱化这些已验证行为。

#### S11-INFO-02 — `DEFAULT_REGISTRY` 仍依赖调用方显式导入 builtin 模块

- **位置**：`agent_mini/tools/builtin/__init__.py`；`agent_mini/tools/registry.py:201`；仓库导入引用扫描。
- **观察**：全新进程只导入 registry 时不会自动加载 write_file；当前测试通过直接导入模块触发装饰器注册。S11 尚无组合根，因此不作为本阶段核心缺陷。
- **建议**：S12/M2 收口或 S18 组合根落地时建立显式 builtin 装载清单，并测试六个工具一次性可见；不要靠测试导入顺序。

#### S11-INFO-03 — 文件 fsync 不等于目录项持久化

- **位置**：`write_file.py:119-125`；write-file 主规格:22-29。
- **观察**：实现保证正常运行时的原子 replace，但未 fsync 父目录；POSIX 断电/崩溃后的 rename 持久性不在当前规格中。
- **建议**：若 S18/交付环境要求 crash durability，再补平台化目录 fsync 与故障注入；否则在设计中明确只承诺进程运行期原子可见性。

#### S11-INFO-04 — hypothesis 与 pytest 版本策略是继承债务

- **位置**：`Docs/DESIGN.md:34`、`pyproject.toml:18-25`、`tests/unit/test_packaging_config.py:12-18`。
- **观察**：设计称沙箱使用 hypothesis，但依赖/测试仍未落地；pytest 只有 `>=8.0`，新 venv 实际解析到 9.1.1，本次仍全绿。
- **建议**：安全竞态与路径组合修复时决定落地或删除 hypothesis 声明；如需完全可复现，再为 pytest 增加兼容上界/锁文件策略。

## 5. 需求—实现—测试追溯表

| FR / TC | 实现位置 | 测试位置 | 覆盖 | 越界/缺口 |
| --- | --- | --- | --- | --- |
| UC-06 | `write_file` + `read_file` 往返 | `test_write_then_read_roundtrip`、空内容测试 | 是（单请求） | 无 Agent/HTTP 闭环；竞态可越界 |
| FR-TOOL-06 | `write_file.py:25-128` | S11 的 19 个参数化实例 | 部分 | 默认不覆盖与沙箱内写入在竞态下失败 |
| FR-TOOL-07（复用） | `Sandbox.resolve` | S10 路径用例 + S11 symlink 用例 | 部分 | junction 交换竞态；设备名集合不完整 |
| TC-L1-012 写分支 | `_prepare` 按编码后字节数检查 | `test_size_limit_does_not_write` | 基本覆盖 | 未验证已有目标在 overwrite=true+超限时保持不变 |
| TC-L4-002 | 无 S11 HTTP 实现 | 无 | 否 | TESTING 定义为 calculator；错误映射，留 S18 也无法验收文件写入 |
| TC-L5-003 相关边界 | Sandbox + write_file | unit marker 中的路径/symlink 样例 | 部分 | 无独立 L5 套件、属性测试或真实竞态防护 |
| NFR-TEST-01 / AC-16 | pytest-cov | 全量覆盖率命令 | 是 | 97%，新增模块 100%；行覆盖不代表并发语义覆盖 |

## 6. 边界抽查结论

- **是否越界实现 search、Memory、HTTP、重试/退避/状态分类：否。** S11 只交付 write_file 与必要文档/测试。
- **普通静态越界、外部 symlink 是否阻断：是。** `../`、绝对路径、隐藏路径和预先存在的外部 symlink 均返回领域错误。
- **resolve 后目录被换为 junction 时是否仍安全：否。** 已复现沙箱外文件写入，P0。
- **默认不覆盖是否对并发创建成立：否。** 已复现 `overwrite=false` 覆盖竞争者文件，且元数据误报未覆盖，P0。
- **TC-L1-012 是否按编码后字节数限制：是。** 2KB/1KB 被拒且不创建；中文等多字节内容按 bytes 计数。
- **超限/编码/校验失败是否在临时文件创建前返回：普通路径是。** 对应测试确认无 `.write-*` 残留。
- **replace 失败是否清理：新目标场景是。** 已有目标保持原值、权限保留和 fsync 调用缺直接断言。
- **可信 sandbox_root/max_file_size 是否暴露给模型：Schema 不暴露。** 但 S11 未通过 Registry 专项测试验证伪造字段。
- **TC-L4-002 是否验证 write_file：否。** 它当前是 calculator HTTP 用例，且 HTTP 留 S18。
- **S10 报告修复是否在 S11 开工前闭环：大部分是。** 修复 change 在 `faa4f73` 前归档且门禁通过；但设备名范围仍不完整，已披露 TOCTOU 在写路径升级为 P0。
- **S00 占位测试是否更新：是。** write_file 已加入结构清单和非占位集合；但包级 docstring 文案仍过期。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S12 / M2 | 六工具可见性依赖隐式模块导入 | 组合根只导入 registry/builtin 包 | S12 收口时增加显式装载与注册表清单测试 |
| S12 / S18 | 默认不覆盖失效并造成数据损坏 | 两个请求同时写同一路径，至少一个 overwrite=false | **S12 前修复 P0-02** |
| S18 | 沙箱外写入 | HTTP 并发或本地不可信进程可改沙箱父目录/junction | **S12 前修复 P0-01**，S18 再做并发 E2E |
| S18 | TC-L4-002 不能验收文件工具 | 只执行当前 calculator 用例 | S12 前先修追溯，S18 实现独立文件 E2E |
| S21 | root/limit 配置与组合装载分散 | 配置容器接管 ToolContext | S21 统一注入，禁止模型覆盖并冻结每请求配置 |
| 跨平台交付 | Windows 设备名与路径规范化不全 | COM5–9/LPT4–9 或变体 | S12 前补齐；Windows CI 固定运行安全集 |
| 崩溃恢复 | rename 后目录项未持久化 | POSIX 断电/进程崩溃且要求 durable write | 需求明确时补目录 fsync；否则文档限定承诺 |

## 8. 总体结论

**S11 暂不可进入 S12。** 普通单请求路径完成度高：19 个阶段测试、243 个全量测试、97% 覆盖率、ruff/format/mypy/OpenSpec/wheel/Python 3.11 隔离复现全部通过；范围控制、编码后字节限制、静态沙箱校验、失败清理和 read_file 往返均有效。

但“默认不覆盖”和“沙箱内写入”两个核心安全承诺都可在确定性竞态下被突破，并分别造成数据覆盖和真实 root 外写入。按项目自己的缺陷分级均为 P0；同时 Windows 设备名、TC 映射、测试统计与 Prompt 时机存在 P1，阶段 DoD 不成立。

进入 S12 前必须处理：

1. **S11-P0-01**：消除或以可验证的 OS 级机制封闭 resolve→create/replace 的父目录替换竞态。
2. **S11-P0-02**：为 overwrite=false 实现原子“不存在才发布”，并补并发回归测试。
3. **S11-P1-01**：补全 Windows 设备名/规范化校验及 read/write 测试。
4. **S11-P1-02**：为文件读写建立真实 E2E TC，修正 TC-L4-002 错误映射。
5. **S11-P1-03**：统一 TESTING 自动化计数和层级执行口径。
6. **S11-P1-04**：登记 Prompt 留痕时序偏差，并保证后续阶段在实现提交前记录。

可选建议：补权限/已有目标失败/Registry/fsync 测试；统一直接 handler 类型错误；清理文档 BOM/EOF 与版本元数据；在 M2 建立显式 builtin 装载清单。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked 改动；HEAD 与 `origin/main` 均为 `d12eb65`。
- **报告落盘前**：tracked 工作区仍干净。
- **报告落盘后预期**：仅新增 `Docs/S11-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec、README、MEMORY 或远程状态，未提交、未推送。
- 测试/构建更新了被忽略的 `.coverage`（14:46）、`agent_mini.egg-info/`（14:49）以及若干 `__pycache__/`；`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/` 已存在。本次按评估边界未清理，普通 `git status` 不显示。
- 隔离验证目录保留于 `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s11-audit-644e0e73fa184d238c4279156732041d`，包含 wheel 与 Python 3.11 venv；需人工确认路径后清理。
- 竞态和设备名探针均使用系统临时目录；临时文件与 junction 已由临时目录上下文清理，未写入仓库或外部业务目录。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S11-P0-01 父目录替换 | 临时文件创建后、发布前复核 parent/temp 的 root containment；失败 path_escape 并清理 | `test_parent_swap_before_publish_is_blocked` |
| S11-P0-02 并发覆盖 | overwrite=false 改用同目录 `os.link` 原子发布；EEXIST→file_exists；overwrite=true 才 replace | `test_concurrent_create_is_not_overwritten` |
| S11-P1-01 设备名 | 生成 COM1–COM9/LPT1–LPT9 完整集合 | COM9/LPT9 测试 |
| S11-P1-02 TC-L4-002 | 从文件需求/PLAN 移除错误映射；文件 E2E 待 S18 新增 | REQUIREMENT/PLAN/TESTING 已改 |
| S11-P1-03 计数 | 统一为 247 passed、unit 183、coverage 97.06% | 全量复跑 |
| S11-P1-04 Prompt 时序 | 历史无法回改；在 ISSUE-038 记录偏差，后续先留 Prompt 再提交 | ISSUE-038 |
| S11-P2-01 缺少直接测试 | 补 P0/设备名/增长/编码测试 | 21 个 write_file 测试 |
| S11-P2-02 handler 类型泄漏 | content/overwrite 显式结构化校验 | invalid_content/invalid_overwrite |
| S11-P2-03/04 格式 | ruff/format 复核 | 64 files formatted |

**复验**：247 passed；unit 183、contract 64；覆盖率 **97.06%**；mypy 61 files 0 errors；OpenSpec 11 passed；wheel/仓库外导入通过。S11 可进入 S12。
