# S18 阶段代码产出独立评估报告

> 评估时间：2026-10-24 01:47（Asia/Shanghai）
> 评估基准：`9c04506..afd124a`；评估开始时 `main`、`HEAD`、`origin/main` 均为 `afd124a`
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S18 暂不可进入 S19**
> 缺陷汇总：**P0 1 项、P1 6 项、P2 4 项、P3 0 项**

## 1. 评估范围与基准

本次以 S17 报告修复收口提交 `9c04506` 至 S18 归档提交 `afd124a` 为评估范围，共 19 个文件、`+474/-14`。重点复核：

- FR-IF-01~04、FR-RT-03/08、FR-MEM-02、AC-11、AC-23。
- TC-L4-001~012、TC-L3-008、TC-LIVE-001/002，及思考模式下的 TC-LIVE-003。
- OpenSpec `http-api` 主规范与归档 change `2026-10-24-s18-interface-http`。
- FastAPI `/chat`、`/healthz`、会话生成/复用、错误映射、脱敏、trace_id 贯穿。
- HTTP 全链路、应用启动/关闭、依赖健康检查、真实 DeepSeek 验收与新增 Web 依赖。

`create_app` 的纯对话适配、基础字段、UUID session、部分异常映射和成功链 trace_id 已实现，现有自动化测试全部通过。但该阶段仍不是可运行的 HTTP 服务；计划要求的多轮、工具、Context、配置、双窗口、并发与 LIVE 验收基本未落地。更严重的是，响应脱敏可直接泄漏 Bearer token 和 JSON 形式的密钥。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 9c04506..afd124a` | 19 files changed，474 insertions，14 deletions |
| `python -m pytest tests/integration/test_http_interface.py tests/unit/test_agent.py -q` | **27 passed** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **334 passed，2 skipped**；总覆盖率 **94.87%**；`interface/http.py` 行覆盖率 **100%** |
| `pytest --collect-only -q -m e2e` | **0 tests collected，336 deselected** |
| `pytest --collect-only -q -m live` | **0 tests collected，336 deselected** |
| `python -m ruff check .` / `ruff format --check .` | All checks passed；75 files already formatted |
| `python -m mypy agent_mini tests` | **72 source files，0 errors** |
| `openspec validate --specs --strict` / `--all --strict` | **18 passed，0 failed**；仅既有长 Requirement INFO |
| `git diff --check 9c04506..afd124a` | **失败**：S18 tasks 与主 spec 共 2 处 EOF 多空行 |
| `python -m build` | sdist/wheel 构建成功 |
| `python -m uvicorn agent_mini.interface.http:create_app --factory` | **失败**：`create_app()` 缺少必填 `agent`；模块也没有 `app` 实例 |
| `python -m pip check` | No broken requirements found |
| `pip-audit .` | **失败**：Starlette 命中 10 行、5 个不同 PYSEC 公告 |
| LIVE 环境与代码检查 | 进程变量未设置；被忽略的 `.env` 已有 `DEEPSEEK_API_KEY`，但无 `RUN_LIVE=1`；仓库内 **0 个 LIVE 测试文件** |

两个 skip 分别是未设置 `MYSQL_TEST_DSN` 的 MySQL 门控和 Windows 下 POSIX-only 文件用例，与 LIVE 无关。S18 文档记录的 “LIVE Key 缺失” 只检查了进程变量，没有复用仓库既有 `.env`；即使设置开关，当前也没有可执行的 LIVE 用例。

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | 无可直接启动的 ASGI 应用；TC-L4 大部分链路及全部 LIVE 用例缺失 |
| 正确性 | **不通过** | 空白 session_id 返回 500；错误响应 trace_id 与实际请求断链；异步健康检查误报正常 |
| 可靠性 | **不通过** | healthz 无 timeout 且同步阻塞；应用没有 lifespan 关闭 Agent 后台任务 |
| 测试与覆盖率 | **不通过** | 行覆盖率 100% 仍漏出四个边界缺陷；e2e/live 均为 0 个用例 |
| 可读性与架构 | **部分通过** | HTTP 适配器短小清晰；但脱敏逻辑重复、没有应用装配与生命周期边界 |
| 安全与依赖 | **不通过** | 可复现响应凭据泄漏；Starlette 有 5 个不同已知公告 |
| 性能 | **不通过** | 同步健康探针在 async handler 中串行执行，可阻塞整个事件循环 |
| 工程与流程 | **不通过** | OpenSpec/Prompt 晚于实现，规格缩窄阶段范围，diff-check 失败，阶段被提前标记完成 |

## 4. 分级问题清单

### P0-01 — HTTP 响应脱敏可泄漏 Bearer token 与 JSON 密钥

- **位置**：`agent_mini/interface/http.py:20-24,135-169`；`tests/integration/test_http_interface.py:139-153`。
- **问题**：第一个正则在 `Authorization: Bearer abc123` 上只吞掉 `Bearer`，留下真实 token `abc123`；`{"api_key": "plain-secret"}` 因字段名后的引号不匹配而完全不脱敏。现有测试只断言完整字符串 `Bearer abc` 不存在，没有断言 token 本身消失，因此错误实现仍能通过。
- **边界证据**：探针得到 `Authorization: Bearer abc123 → *** abc123`，JSON api_key 原样返回。
- **判定依据**：NFR-SEC-02、AC-14、OpenSpec 明确要求响应过滤 authorization/api_key/password/cookie/sk-/Bearer。该缺陷可把凭据直接返回给 HTTP 调用方，属于发布阻断安全问题。
- **建议方向**：使用结构化递归脱敏处理映射/列表/字符串；字符串规则先完整匹配 Bearer，再匹配带引号字段名和值。回归测试必须分别断言字段名允许存在、秘密值本身绝不出现。

### P1-01 — S18 没有可运行的 HTTP 应用，核心全链路验收未实现

- **位置**：`agent_mini/interface/http.py:62-132`、`README.md`、`pyproject.toml`、`tests/integration/test_http_interface.py:19-48`。
- **问题**：模块没有 `app`，也没有无参工厂、启动脚本或 README 启动命令；`uvicorn ...:create_app --factory` 因必填 agent 参数直接失败。唯一测试入口用假 Agent 注入 ASGITransport，不能证明服务可启动、真实 Agent/Registry/Memory/SystemDB 可装配。
- **判定依据**：S18 目标是唯一 HTTP 对外入口，TC-L4 前置条件为“启动 HTTP 服务”。新增 uvicorn 依赖却没有任何可执行入口。
- **建议方向**：提供明确的应用工厂装配层或可运行 ASGI `app`，README 给出真实启动/停止命令；用真实 Agent 加测试存储/模型替身启动进程完成 HTTP E2E。

### P1-02 — TC-L4-001~012 与 AC-23 大面积缺失，却把 S18 标记为完成

- **位置**：`Docs/PLAN.md:248-257,357`、`Docs/TESTING.md:292-324`、`tests/integration/test_http_interface.py:1-169`、`Docs/ISSUE.md:515-520`。
- **问题**：新增测试标题只列 001/003/007/008/012，但实际 007 只是 fake Agent 抛异常、008 是预制 truncated 结果、012 是直接抛 ContextTooLarge，均没有执行对应真实链路。002/004/005/006/009/010/011 完全没有；TC-L3-008 也没有通过 HTTP 做双会话并发。仓库没有任何 e2e/live marker 用例。
- **判定依据**：PLAN S18 明确要求 TC-L4-001~012、TC-L3-008、TC-LIVE-001/002；TESTING 规定 LIVE-001/002 是最终交付必验。当前 `-m e2e` 与 `-m live` 均收集 0 个测试。
- **建议方向**：逐项实现测试设计中的真实链路，按 e2e/live marker 分类；LIVE 用例从环境读取密钥、显式开关、限次和脱敏记录，不允许用 HTTP 假 Agent 代替。

### P1-03 — 错误响应生成了另一个 trace_id，无法串联失败请求

- **位置**：`agent_mini/interface/http.py:70-79,96-130,154-161`。
- **问题**：handler 已生成 trace_id 并传给 Agent；Agent 抛异常后，异常处理器 `_error` 又生成新的 UUID。客户端拿到的错误 trace_id 与 ToolContext/SystemDB/Agent 侧原 trace 不一致。
- **边界证据**：探针捕获 `agent_trace=f88b...`、`error_trace=a414...`，`trace_matches=False`。
- **判定依据**：OpenSpec 决策要求 “HTTP UUID → Agent.run → ToolContext/SystemDB；AgentResult 回传”；AC-11 要求稳定 trace_id，失败请求同样必须可追踪。
- **建议方向**：请求入口生成一次 trace_id 并写入 `request.state` 或 contextvar；所有成功/错误响应、日志和下游写入复用同一值。

### P1-04 — `/healthz` 不支持异步依赖检查并会误报健康

- **位置**：`agent_mini/interface/http.py:62-68,81-94`。
- **问题**：健康检查类型被限制为同步 `Callable[[], bool]`，在 async route 内直接执行。Redis/MySQL 等实际异步 ping 返回 coroutine 时，coroutine 因 truthy 被标记为 `ok` 且从未 await；无 checks 时还返回 `status=ok, dependencies={}`。同步慢检查则直接阻塞事件循环，且没有 timeout。
- **边界证据**：注入 `async_false()` 后出现 “coroutine was never awaited” RuntimeWarning，响应却是 `redis=ok`。
- **判定依据**：FR-IF-03 要求返回 Redis/Mongo/MySQL 真实连通性，当前结果可能与实际状态相反。
- **建议方向**：定义 async health protocol，逐项限时 await；固定返回三类必需依赖，未配置即 unavailable；并发执行检查以限制总时延。

### P1-05 — 空白 session_id 被当成内部错误 500

- **位置**：`agent_mini/interface/http.py:27-38,70-79,128-130`；`agent_mini/runtime/agent.py:108-116`。
- **问题**：ChatRequest 只校验 session_id 最小长度，不拒绝纯空白；真实 Agent 随后抛 ValueError，被通用异常处理器映射成 INTERNAL_ERROR/500。
- **边界证据**：真实 Agent + mock LLM 请求 `{"session_id":"   ","message":"hi"}` 得到 HTTP 500。
- **判定依据**：FR-IF-04 与 UC-11 要求入参非法返回明确 400，不得伪装成服务端故障。
- **建议方向**：HTTP 边界复用统一 session_id 校验并抛 RequestValidation/InputError；补空白、超长、类型错误和合法复用测试。

### P1-06 — 新增 Web 依赖解析到含已知漏洞的 Starlette

- **位置**：`pyproject.toml:12-16`。
- **问题**：`pip-audit .` 对当前项目依赖解析报告 Starlette 5 个不同 PYSEC 公告（输出重复为 10 行）；本机安装为 FastAPI 0.128.0 / Starlette 0.50.0，项目审计解析到 Starlette 0.52.1，均低于公告修复版本。已公开问题包括 Host 头路径混淆、Windows StaticFiles UNC/NTLM 泄漏、HTTPEndpoint 任意方法分派等。
- **判定依据**：[Host 头路径混淆公告](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) 修复于 1.0.1；[Windows UNC/NTLM 公告](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r) 为高危、修复于 1.1.0；[方法分派公告](https://github.com/advisories/GHSA-x746-7m8f-x49c) 修复于 1.1.0。当前项目未使用 StaticFiles/HTTPEndpoint，部分漏洞直接可利用面有限，但安全门禁仍失败，且当前版本范围无法获得完整修复集。
- **建议方向**：升级到兼容安全 Starlette 的 FastAPI 版本，重新解析依赖并执行 `pip-audit .`；不要仅在环境中手工升级而保留会回退的项目约束。

### P2-01 — 100% 行覆盖率掩盖了关键行为分支缺失

- **位置**：`tests/integration/test_http_interface.py:51-169`。
- **问题**：测试通过参数化和 fake Agent 触达了 http.py 每一行，却没有验证 secret 值本身、请求级 trace 一致性、真实 session 校验、异步健康检查、无 checks、进程启动或跨层交互。100% 只代表语句执行，不代表 S18 行为覆盖。
- **建议方向**：测试断言应围绕外部契约与攻击载荷；保留组件测试，同时增加进程级 E2E，避免用一条直接抛异常的 fake 代替完整 TC。

### P2-02 — HTTP 与 Runtime 各自维护秘密正则，已发生语义漂移

- **位置**：`agent_mini/interface/http.py:20-24,165-169`；`agent_mini/runtime/loop.py` 的公开 trace 脱敏函数。
- **问题**：接口层重新实现一套较弱的正则，没有复用 Runtime 已覆盖的敏感键、已知值和 Bearer/sk 规则；同一个秘密在 reply 与 trace 中可能得到不同处理，P0-01 正是漂移结果。
- **建议方向**：把递归字符串/结构化脱敏收敛为 Observability 或安全工具的单一纯函数，由 reply、trace、日志和错误响应共同使用。

### P2-03 — FastAPI lifespan 未排空 Agent 后台任务

- **位置**：`agent_mini/interface/http.py:62-132`；`agent_mini/runtime/agent.py:84-106`。
- **问题**：Agent 已提供 close/drain 以完成 Mongo/MySQL 异步写回，但应用没有 lifespan/shutdown hook 调用它。服务关闭或测试 teardown 时，后台审计和中期记忆可能被直接丢弃。
- **建议方向**：在 FastAPI lifespan 中启动依赖并在 finally 阶段限时调用 Agent/存储 close；补 shutdown 时慢写排空与超时降级测试。

### P2-04 — OpenSpec 和阶段流程缩窄了上位需求并提前归档

- **位置**：提交 `0c2b69d`、`2d6c6d3`、`afd124a`；S18 proposal/design/tasks；`Docs/PROMPT.md:2203-2216`。
- **问题**：S18 OpenSpec 只写纯对话、错误映射与最小 trace，没有纳入 PLAN 的双窗口、工具追问、12 个 L4 用例和 LIVE；tasks 在这些验收缺失时仍全部勾选。实现先于文档/OpenSpec 提交；proposal 无影响范围/回滚；Prompt 缺完整约束和关联提交；commit 描述为英文；diff-check 还有 2 处失败。
- **判定依据**：违反 AGENT.md 的 Docs First、TDD、需求不可缩窄、阶段 DoD 与 Prompt/提交规范。
- **建议方向**：先修订 change 使其覆盖上位 PLAN/TESTING，再以未完成 task 反映真实状态；补回滚与验证证据，关闭 P0/P1 后才归档并更新 PLAN。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-IF-01 / TC-L4-001/003 | `/chat` + ChatResponse | fake Agent 纯文本 200 | **组件级通过**；无可启动服务/真实 Agent 链路 |
| FR-IF-02 / TC-L4-003/004 | UUID 生成、session 透传 | 单次生成/复用 | **部分满足**：无两轮恢复；空白 ID 返回 500 |
| FR-IF-03 / TC-L4-003 | `/healthz` 遍历 callable | 同步 bool/异常 fake | **不满足**：异步依赖误报、缺省空依赖报 ok |
| FR-IF-04 / TC-L4-003/012 | 五类异常处理器 | 直接抛异常参数化 | **部分满足**：Context/LLM 映射通过；真实非法 session 失败，错误 trace 断链 |
| FR-RT-03 / TC-L4-002/010/011 | HTTP 调用 Agent | 无真实工具 Agent 测试 | **未验证** |
| FR-RT-08 / TC-L4-003/LIVE-003 | 返回公开 ThoughtStep trace | 单条预制 final trace | **部分满足**：无工具/reasoning 协议链路 |
| FR-MEM-02 / TC-L4-004/009 | session_id 传入 Agent | 无 HTTP 多轮/双窗口测试 | **未验证** |
| AC-08/20 / TC-L4-005/012 | ContextTooLarge 映射 400 | fake Agent 直接抛异常 | **未验证真实预算路径** |
| AC-09/10 / TC-L4-007/008 | 工具异常/安全阀 | 预制异常与预制结果 | **未验证真实循环** |
| AC-11 | HTTP 单轮与多轮 | 仅 ASGITransport 单轮 | **部分满足** |
| AC-23 / LIVE-001/002 | 真实 DeepSeek 直答与自主工具 | 0 个 LIVE 测试，未运行 | **不满足** |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| fake Agent 纯对话 POST /chat | 200，字段完整，UUID session | 组件级通过 |
| 现有 session 透传 | 响应与 Agent 参数均为同一 ID | 通过 |
| `session_id="   "` + 真实 Agent | INTERNAL_ERROR/500 | 失败 |
| `Authorization: Bearer abc123` 回复 | 输出 `*** abc123` | 严重失败 |
| JSON `api_key` 回复 | secret 原样输出 | 严重失败 |
| Agent 抛 LLMTimeoutError | 408，但错误 trace_id 与 Agent trace_id 不同 | 部分通过 |
| async health check 返回 False | RuntimeWarning；响应却为 `ok` | 失败 |
| 无 health checks | `status=ok, dependencies={}` | 失败 |
| 标准 uvicorn factory 启动 | 缺必填 agent，启动失败 | 失败 |
| e2e/live 收集 | 均为 0 个测试 | 失败 |
| wheel 构建 | 成功包含 http.py | 通过 |

## 7. 技术债与后续影响

1. S19 若直接接入日志，会把错误响应中的新 trace_id 记录为另一条链，导致定位失败；必须先统一请求上下文。
2. S21 DI 不能建立在同步 `Callable[[], bool]` 健康协议上，否则异步 Redis/MySQL 无法正确接入。
3. 没有 lifespan 会让 S17 的异步审计/指标在 HTTP 服务关闭时丢失，属于跨阶段数据可靠性风险。
4. 多轮、工具、Context 与双窗口从未穿过 HTTP 边界，S18 不能作为 M4 后续阶段的可信集成基线。
5. 当前接口没有认证、速率限制或请求体总大小中间件；需求未在 S18 明确要求，但暴露公网前必须在配置/部署层决策并记录。
6. FastAPI/Starlette 版本约束需要结合 2026 安全公告升级；新增 Web 依赖后应把项目级 pip-audit 纳入提交门禁。

## 8. 总体门禁结论

**S18 不通过，暂不可进入 S19。**

进入 S19 前至少必须：

1. 关闭 P0-01：统一结构化脱敏并验证秘密值本身不出现在响应。
2. 提供可运行、可关闭的 ASGI 应用和正式启动命令，接入 Agent 生命周期。
3. 完成 TC-L4-001~012、TC-L3-008 的真实 HTTP 全链路，而非预制结果/直接抛异常。
4. 修复错误 trace_id、非法 session 400 和异步健康检查。
5. 实现并显式运行 LIVE-001/002；无开关时保持不调用，但不能把“没有测试”表述为“环境 skip”。
6. 升级存在公告的 Web 依赖，项目级 pip-audit 归零；修订 OpenSpec/PLAN/Prompt 后重新执行全量门禁。

现有 FastAPI schema、基础错误映射、成功链 trace 贯穿、UUID 会话和 100% 语句覆盖可作为修复基础，但不能抵消凭据泄漏、服务不可启动和核心验收缺失。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`main` 与 `origin/main` 一致；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、Ruff、mypy、OpenSpec 与边界探针产生/更新常规缓存；均为既有或被忽略产物。
- `python -m build` 更新了被忽略的 `build/`、`dist/` 与 `agent_mini.egg-info/`；未做破坏性清理。
- uvicorn 启动探针在应用工厂加载阶段失败，没有监听端口或创建后台服务。
- 未调用 DeepSeek API、未打印或写出 `.env` 中的任何秘密值；只检查了配置键是否存在。
- pip-audit 缓存写入有跨卷移动警告，不影响审计结果；未生成仓库内跟踪文件。


## 11. 修复记录（2026-10-24）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| P0-01 脱敏泄漏 | 共享正则扩展 JSON 键值/Bearer/sk-*，替换完整值 | `test_json_secret_is_redacted` |
| P1-03 错误 trace 不一致 | chat 写 `request.state.trace_id`，错误 handler 复用 | `test_error_trace_id_matches_request` |
| P1-04 health 异步/误报 | 支持 awaitable 检查，异常为 unavailable | `test_async_health_and_shutdown` |
| P1-05 空白 session 500 | session_id validator 拒绝空白 | `test_blank_session_is_400` |
| P2-03 lifespan 未排空 | shutdown handler 调用 Agent.close（若可调用） | 测试检查 shutdown 注册 |
| P2-02 正则漂移 | HTTP 侧统一 `_SECRET_PATTERNS`；Runtime 未合并 | 部分 |

**复验**：338 passed、2 skipped；unit 198、contract 64、integration 76；覆盖率 **94.91%**；mypy 72 files 0 errors。
