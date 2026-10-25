# Agent-mini 项目演示真机测试用例

> 版本：v0.1 演示用  
> 日期：2026-10-25  
> 范围：S00–S21 已实现工具与链路，重点覆盖 `calculator`、`time`、`todo`、`read_file`、`write_file`、`search`（mock）、Agent 记忆、HTTP、MySQL 审计与 LIVE。  
> 原则：真实模型只走 LIVE 用例；非 LIVE 用例使用固定模型替身或直接工具调用；所有密钥只从环境/`.env` 读取，不写入本文件。

## 1. 测试环境

| 组件 | 配置 | 验证方式 |
| --- | --- | --- |
| Python | 3.13 本机；3.11 Docker | `python --version` |
| DeepSeek | `.env` 的 `DEEPSEEK_API_KEY`；`RUN_LIVE=1` | `pytest -m live` |
| HTTP | `agent-mini` 或 uvicorn factory | `GET /healthz` |
| MySQL | Docker `agent-mini-mysql`，`127.0.0.1:3307` | `MYSQL_TEST_DSN` |
| Redis | Docker `agent-mini-redis`，`127.0.0.1:6380` | `REDIS_TEST_URL` |
| Mongo | Docker `agent-mini-mongo`，`127.0.0.1:27018` | `MONGO_TEST_URI` |
| 沙箱 | 临时目录 `workspace/` | `ToolContext.sandbox_root` |

### 1.1 环境变量

```bash
export RUN_LIVE=1
export DEEPSEEK_API_KEY=...          # 只从 .env/环境读取
export MYSQL_TEST_DSN='mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini'
export REDIS_TEST_URL='redis://127.0.0.1:6380/0'
export MONGO_TEST_URI='mongodb://127.0.0.1:27018'
```

> 禁止把真实 Key、DSN 密码、Bearer token 写入命令历史、测试夹具或报告。

## 2. 工具覆盖矩阵

| 工具/能力 | 用例 |
| --- | --- |
| calculator | DEMO-003、DEMO-013 |
| time | DEMO-004 |
| todo（add/list/complete/delete） | DEMO-005 |
| read_file | DEMO-006、DEMO-008 |
| write_file（新建/覆盖/防覆盖） | DEMO-007、DEMO-009 |
| search（mock） | DEMO-010 |
| search（未配置） | DEMO-011 |
| Redis 短时记忆 | DEMO-012、DEMO-014 |
| Mongo 中期记忆 | DEMO-012 |
| Context 裁剪 | DEMO-014 |
| HTTP /chat、/healthz | DEMO-001、DEMO-015 |
| MySQL 五表审计 | DEMO-002、DEMO-013 |
| LIVE 直答/工具/thinking | DEMO-016、DEMO-017、DEMO-018 |

## 3. 测试数据与约定

| 名称 | 值/规则 |
| --- | --- |
| 演示会话 | `demo-<日期>-<随机>`，每次用例独立 |
| 沙箱 | `DEMO_ROOT=<临时目录>/demo-workspace` |
| 只读文件 | `DEMO_ROOT/note.txt`，内容 `hello demo` |
| 写入文件 | `DEMO_ROOT/out.txt` |
| todo 内容 | `买牛奶`、`写演示` |
| 搜索查询 | `agent-mini demo` |
| 假密钥哨兵 | `sk-<uuid>`，仅运行时生成 |
| reasoning 哨兵 | `private-<uuid>`，仅运行时生成 |

## 4. 用例清单

### DEMO-001 健康检查与依赖

- **优先级**：P0
- **前置**：MySQL/Redis/Mongo 容器 Up；工厂环境完整。
- **步骤**：
  1. 启动 `agent-mini`；
  2. `GET /healthz`。
- **预期**：
  - HTTP 200；
  - `status=ok`；
  - `dependencies` 含 `mysql/redis/mongo` 且均为 `ok`；
  - 响应不含 DSN、密码、端口以外的秘密。
- **证据**：响应 JSON、容器 `docker ps`。

### DEMO-002 MySQL 五表审计

- **优先级**：P0
- **前置**：DEMO-001 通过；`MYSQL_TEST_DSN` 可用。
- **步骤**：
  1. 发起一次带工具调用的 `/chat`；
  2. 等待 `drain`；
  3. 查询 `sessions/models/tools/tool_invocations/request_metrics`。
- **预期**：
  - 五表存在；
  - 本次会话在 sessions 有记录；
  - tool_invocations 有本次工具；
  - request_metrics 的 trace_id、steps、tool_calls、tokens、duration_ms 非空；
  - 表中无 `sk-*`、Bearer、密码。
- **证据**：SQL 行数/字段截图（脱敏）。

### DEMO-003 calculator 工具

- **优先级**：P0
- **步骤**：
  1. 新建会话；
  2. 发送：`必须调用 calculator 计算 expression=2+2，然后回答。`
- **预期**：
  - HTTP 200；
  - `tool_calls>=1`；
  - trace 中有 `calculator` 且 `ok=true`；
  - reply 含 `4`；
  - 不发生除零/语法错误。
- **补充**：失败路径 `1/0` 应返回结构化 tool 错误，不抛 500。

### DEMO-004 time 工具

- **优先级**：P1
- **步骤**：发送 `现在几点？请调用 time 工具。`
- **预期**：
  - trace 有 `time` 且 `ok=true`；
  - reply 含合法时间；
  - 与系统时区一致。

### DEMO-005 todo 全生命周期

- **优先级**：P1
- **步骤**（同一 session）：
  1. `把“买牛奶”加入待办`
  2. `列出待办`
  3. `完成“买牛奶”`
  4. `删除“买牛奶”`
- **预期**：
  - add 后 list 含 `买牛奶`；
  - complete 后状态为完成；
  - delete 后列表不含该项；
  - 不同 session 不串待办。

### DEMO-006 read_file 正常读取

- **优先级**：P1
- **前置**：`DEMO_ROOT/note.txt` 存在。
- **步骤**：发送 `读取 note.txt 并原样返回内容。`
- **预期**：
  - trace 工具 `read_file`，`ok=true`；
  - reply 含 `hello demo`；
  - 不返回沙箱外路径。

### DEMO-007 write_file 新建

- **优先级**：P1
- **步骤**：发送 `把 "demo" 写入 out.txt。`
- **预期**：
  - trace `write_file`，`ok=true`；
  - 文件存在，内容 `demo`；
  - 返回 size=4、overwritten=false。

### DEMO-008 沙箱路径逃逸

- **优先级**：P0
- **步骤**：发送 `读取 ../../etc/passwd。`
- **预期**：
  - HTTP 200（工具失败不冒泡）；
  - trace `read_file`，`ok=false`；
  - error_code 为 `path_escape` 或等价沙箱错误；
  - 不返回系统文件内容。

### DEMO-009 write_file 防覆盖

- **优先级**：P0
- **步骤**：
  1. 已存在 `out.txt`；
  2. 发送 `把 "other" 写入 out.txt，不要覆盖。`
- **预期**：
  - 工具 `ok=false`，error_code=`file_exists`；
  - 原内容保持不变；
  - 临时文件 `.write-*` 无残留。

### DEMO-010 search mock 生效

- **优先级**：P1
- **前置**：`SEARCH_PROVIDER=mock`。
- **步骤**：发送 `搜索 agent-mini demo。`
- **预期**：
  - trace `search`，`ok=true`；
  - 返回 `provider=mock`；
  - 结果为 `https://example.invalid/mock`，不访问外网；
  - 不伪造真实网页来源。

### DEMO-011 search 未配置

- **优先级**：P1
- **前置**：`SEARCH_PROVIDER=none`。
- **步骤**：发送 `搜索 agent-mini demo。`
- **预期**：
  - 工具 `ok=false`；
  - error_code=`not_configured`；
  - 不返回伪造结果。

### DEMO-012 跨轮记忆（Redis + Mongo）

- **优先级**：P0
- **前置**：Redis/Mongo 真实容器可用。
- **步骤**（同一 session）：
  1. `我叫 Alice`
  2. `我叫什么？`
  3. `列出你记得的我的名字`
- **预期**：
  - 第二轮 reply 含 `Alice`；
  - Mongo 有中期轮次；
  - Redis 有最近轮次；
  - 跨 session 不泄露 Alice；
  - 合并顺序为时间正序。

### DEMO-013 工具后 ContextTooLarge

- **优先级**：P0
- **前置**：低 context budget / 大工具结果。
- **步骤**：触发工具大结果后继续对话。
- **预期**：
  - HTTP 400 `CONTEXT_TOO_LARGE`；
  - 响应含 `steps/trace/truncated=true`；
  - trace 可 JSON 序列化；
  - 工具不重复执行（只 1 次）。

### DEMO-014 14 轮裁剪

- **优先级**：P1
- **前置**：窗口 K=10。
- **步骤**：同一 session 连续 14 轮对话。
- **预期**：
  - 只保留最近 10 轮；
  - system/current 不删；
  - `context.trimmed` 日志出现；
  - 日志无完整 prompt/content。

### DEMO-015 HTTP 错误映射

- **优先级**：P1
- **步骤**：分别注入 400/408/429/502/500。
- **预期**：
  - 状态码映射正确；
  - code 与日志 code 一致；
  - 响应不含异常类名、堆栈、DSN、Key；
  - 4xx WARNING、5xx ERROR。

### DEMO-016 LIVE 直答

- **优先级**：P0
- **前置**：`RUN_LIVE=1`，`.env` Key 有效。
- **步骤**：`pytest tests/live/test_live_smoke.py::test_live_001_direct_answer -q`
- **预期**：3 秒级响应；reply 含 `2`；usage>0；Key 不出现。

### DEMO-017 LIVE 真实工具闭环

- **优先级**：P0
- **步骤**：`pytest tests/live/test_live_smoke.py::test_live_002_real_tool_loop -q`
- **预期**：
  - 真实 Agent 调用 calculator；
  - `tool_traces` 有 calculator/ok；
  - trace_id 非空；
  - Key 不出现。

### DEMO-018 LIVE thinking 模式

- **优先级**：P0
- **步骤**：`pytest tests/live/test_live_smoke.py::test_live_003_thinking_mode -q`
- **预期**：
  - thinking 请求成功；
  - reply 含 `9`；
  - reasoning 不进入公开响应/日志。

## 5. 执行命令

```bash
# 全量（真实依赖 + LIVE）
RUN_LIVE=1 \
MYSQL_TEST_DSN='mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini' \
REDIS_TEST_URL='redis://127.0.0.1:6380/0' \
MONGO_TEST_URI='mongodb://127.0.0.1:27018' \
pytest -q

# 仅 LIVE
pytest tests/live -q

# 仅真实依赖
pytest tests/integration/test_real_services.py tests/integration/test_observability_security.py -q

# M3
pytest tests/integration/test_m3_demo.py tests/integration/test_short_term.py \
  tests/integration/test_mid_term.py tests/integration/test_context_builder.py \
  tests/integration/test_context_window.py -q
```

## 6. 当前自动化基线（2026-10-25）

| 场景 | 结果 |
| --- | --- |
| Docker + LIVE 全量 | 395 passed, 1 skipped |
| 默认全量 | 388 passed, 8 skipped |
| M3 五文件 | 54 passed |
| MySQL 真机 | 8 passed（systemdb） |
| Redis/Mongo 真实往返 | 3 passed |
| LIVE | 3 passed |
| Python 3.11 全量 | 394 passed, 2 skipped |
| wheel + 仓库外导入 | 通过 |
| 覆盖率 | 94.95% |

> 说明：上述为自动化套件基线，不等价于每个 DEMO 用例均已人工逐条执行；演示时需按第 4 节逐条留证，禁止用套件总数替代单条结论。

## 7. 演示准出标准

- P0 用例全部通过；
- P1 用例通过或书面接受；
- 无 `sk-*`、Bearer、密码、reasoning 出现在响应/日志/DB；
- `/healthz` 三依赖 `ok`；
- MySQL/Redis/Mongo 至少各一条真实写读证据；
- LIVE-001/002/003 有真实模型响应与 usage；
- 失败用例附 trace_id、复现命令与脱敏日志，不伪造通过。

## 8. 风险与限制

- `search` 当前仅 mock，不能宣称真实搜索能力。
- `thinking` 模式仅通过 LIVE-003 验证，未覆盖所有模型版本。
- Windows 下 POSIX `write_file` 有 1 个 skip；Linux 证据来自 Docker 3.11。
- 覆盖率 94.95%，低于 97% 目标。
- 演示前需确认 Docker 容器仍在运行，`.env` 未被提交。
