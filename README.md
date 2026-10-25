# Agent-mini

从零实现的最小 ReAct Agent，覆盖 S00–S21：模型接入、工具循环、安全阀、Redis/Mongo 记忆、Context 裁剪、MySQL 审计、HTTP API、结构化日志、统一异常与轻量 DI。

## 1. 运行方式

### 1.1 环境要求

- Python 3.11+
- Docker（MySQL 8 / Redis 7 / MongoDB 7，真机演示需要）
- DeepSeek API Key（LIVE 验收需要）

### 1.2 安装

```bash
pip install -e ".[dev]"
cp .env.example .env
```

`.env` 只保存本地值，不提交；`.gitignore` 已忽略 `.env`，只保留 `.env.example`。

### 1.3 配置

必填：

| 变量 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 模型调用，禁止写入 tracked 文件 |

可选：

| 变量 | 默认/说明 |
| --- | --- |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | `deepseek-chat` |
| `DEEPSEEK_TIMEOUT` | `60` 秒 |
| `DEEPSEEK_RETRY` | `2`，范围 1–3 |
| `REDIS_URL` | 未配置则不装配短时记忆 |
| `MONGO_URI` | 未配置则不装配中期记忆 |
| `MYSQL_DSN` | 必填；系统库 DSN |
| `MYSQL_POOL_SIZE` / `MYSQL_POOL_TIMEOUT` / `MYSQL_AUTO_CREATE` | 连接池与建表 |
| `SEARCH_PROVIDER` | `none`（默认）或 `mock` |
| `RUN_LIVE` | `1` 时启用真实 API 验收 |

非敏感配置也可放在 `config.yaml`；环境变量覆盖同名 YAML 字段。

### 1.4 启动依赖（Docker）

```bash
docker run --name agent-mini-mysql -e MYSQL_ROOT_PASSWORD=<password> \
  -e MYSQL_DATABASE=agent_mini -p 3307:3306 -d mysql:8.0
docker run --name agent-mini-redis -p 6380:6379 -d redis:7-alpine
docker run --name agent-mini-mongo -p 27018:27017 -d mongo:7
```

示例 `.env`：

```dotenv
DEEPSEEK_API_KEY=
MYSQL_DSN=mysql+asyncmy://root:<password>@127.0.0.1:3307/agent_mini
REDIS_URL=redis://127.0.0.1:6380/0
MONGO_URI=mongodb://127.0.0.1:27018
SEARCH_PROVIDER=mock
RUN_LIVE=0
```

### 1.5 启动 HTTP

```bash
agent-mini
# 或
uvicorn agent_mini.interface.http:create_app_from_env --factory --port 8000
```

`agent-mini` 在配置错误时输出单行错误并退出码 2，不打印堆栈。

```bash
curl http://127.0.0.1:8000/healthz
```

预期：

```json
{"status":"ok","dependencies":{"redis":"ok","mongo":"ok","mysql":"ok"}}
```

### 1.6 调用

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","message":"计算 2+2"}'
```

响应字段：`session_id/reply/steps/tool_calls/usage/trace/trace_id/truncated`。

### 1.7 测试

```bash
pytest -q
pytest -m unit
pytest -m contract
pytest -m integration
RUN_LIVE=1 pytest -m live
```

真机（三 Docker 服务 + LIVE）：

```bash
MYSQL_TEST_DSN='mysql+asyncmy://root:<password>@127.0.0.1:3307/agent_mini' \
REDIS_TEST_URL='redis://127.0.0.1:6380/0' \
MONGO_TEST_URI='mongodb://127.0.0.1:27018' \
RUN_LIVE=1 pytest -q
```

静态检查：

```bash
ruff check .
ruff format --check .
mypy agent_mini tests
```

## 2. 系统设计

```text
HTTP /chat
  │
  ├─ ChatRequest 校验（Pydantic）
  ├─ ContextVar trace_id/session_id
  ├─ Agent.run
  │    ├─ ContextBuilder
  │    │    ├─ Redis 短时记忆（最近轮次）
  │    │    ├─ Mongo 中期记忆（历史轮次）
  │    │    └─ 整轮裁剪 + token 预算
  │    ├─ ReAct Loop
  │    │    ├─ LLMClient（重试/超时）
  │    │    ├─ ToolRegistry / RegistryExecutor
  │    │    └─ 安全阀（max_steps/deadline/重复调用）
  │    ├─ 响应前同步写 Redis
  │    └─ 响应后异步写 Mongo/MySQL
  ├─ JSON 日志 + RedactionFilter
  └─ AgentError → 统一错误响应
```

### 2.1 分层

| 层 | 模块 | 职责 |
| --- | --- | --- |
| 接口 | `interface/http.py`、`server.py` | FastAPI、健康检查、错误映射、启动入口 |
| 运行时 | `runtime/agent.py`、`runtime/loop.py` | 单轮调度、ReAct、安全阀 |
| 模型 | `llm/` | OpenAI 兼容客户端、重试、协议解析 |
| 工具 | `tools/` | 注册表、Schema、calculator/time/todo/read/write/search |
| 记忆 | `memory/` | Redis 短时、Mongo 中期 |
| 上下文 | `context/` | 拼接、token 计数、整轮裁剪 |
| 系统库 | `systemdb/` | MySQL 五表：sessions/models/tools/tool_invocations/request_metrics |
| 可观测 | `observability/` | JSON 日志、脱敏、AgentError |
| 配置/DI | `config/` | 四类配置、YAML+env、轻量容器 |

### 2.2 关键不变量

- 密钥只从环境/`.env` 读取；`SecretStr` 包裹，禁止进入日志/响应/DB。
- `reasoning_content` 不进入公开响应、日志、trace、MySQL。
- 工具 handler 异常转为 `ToolResult(ok=False)`，不冒泡为 500。
- Context 超限本地抛 `ContextTooLarge` → 400，且不重放已执行工具。
- HTTP 无状态；会话状态全部落 Redis/Mongo/MySQL。
- 配置在启动时校验，缺失必填项直接 `ConfigError`。

### 2.3 配置与 DI

- `config.yaml` 非敏感 + env 覆盖；必填 `DEEPSEEK_API_KEY`、`MYSQL_DSN`。
- 四类冻结配置：`ModelConfig` / `ToolConfig` / `PromptConfig` / `SystemDBConfig`。
- 手写 `Container`：工厂 + singleton/transient + `override`；无模块级全局容器。
- 顶层装配 `LLM`、短/中期记忆、SystemDB、ContextBuilder、Agent、HTTP app。
- `search` 当前仅 `mock`；真实 provider 不在 v0.1 范围。

## 3. Memory 的召回时机与放置方式

### 3.1 召回时机

每次 `Agent.run` 开始时，由 `ContextBuilder.build` 召回一次：

1. 若 `session_id` 有效：
   - 从 Mongo 读取中期历史（时间正序，`get_rounds`）；
   - 从 Redis 读取最近轮次（`get_recent_rounds`）；
   - 以 short 尾部为准合并：保留 mid 前缀，拼接完整 short，再追加 mid 尾部缺失轮次；
   - 按 `round_id` 去重。
2. 无 `session_id` 时不召回历史，只发送当前 user 消息。

工具调用后，下一次 LLM 请求前会再次 `fit`，把新增工具往返纳入预算；首次 fit 复用 build 结果，天然只读一次 Memory。

### 3.2 放置方式

发送给模型的顺序固定为：

```text
[system prompt?]
[历史轮次：user/assistant/tool ...，时间正序]
[current user]
```

- system prompt 永远在首位，且不参与裁剪。
- 当前轮（user + 本轮工具往返）不可删。
- 历史按“完整轮次”裁剪，优先丢最旧轮；保留最近 K 轮（默认 10）。
- 超 token 预算时继续整轮删除；仍超则 `ContextTooLarge`。
- reasoning 是否计入 token 由 `include_reasoning` 控制；容器装配与实际 HTTP 发送保持一致（当前为 false）。

### 3.3 写入时机

| 存储 | 时机 | 内容 |
| --- | --- | --- |
| Redis 短时 | 响应返回前同步写 | 当前完整轮次，LTRIM 到 K 轮，TTL 24h |
| Mongo 中期 | 响应后异步写 | 完整轮次 + created_at，后台任务可 drain |
| MySQL | 响应后异步写 | 会话/工具审计/请求指标，不存对话正文 |

写入失败降级为 `memory.degraded`，不阻断主链路；失败轮次可能只存在于 Redis 或 Mongo，下一次召回按上述合并规则尽力恢复顺序。

### 3.4 会话隔离

- Redis key 含 `session_id`；Mongo 查询按 `session_id` 过滤。
- todo 按可信 `ToolContext.session_id` 分区，模型不能指定其他会话。
- 跨会话不可读；无 session 的请求不写记忆。

## 4. 文档索引

| 文档 | 内容 |
| --- | --- |
| [Docs/AIPROMPT.md](Docs/AIPROMPT.md) | **AIPROMPT**：各阶段 AI 执行 Prompt 与摘要索引 |
| [Docs/test-result.md](Docs/test-result.md) | **真机测试完整结果**：命令、HTTP 请求/响应、工具输出、Docker 证据 |
| [Docs/test-report.md](Docs/test-report.md) | 项目演示测试用例（DEMO-001~018） |
| [Docs/ISSUE.md](Docs/ISSUE.md) | **问题台账**：Open/Resolved、ISSUE-024/025/044 等 |
| [Docs/PLAN.md](Docs/PLAN.md) | S00–S21 阶段计划与状态 |
| [Docs/DESIGN.md](Docs/DESIGN.md) | 架构、数据模型、错误/日志/配置设计 |
| [Docs/TESTING.md](Docs/TESTING.md) | TC 定义、marker、计数与覆盖率 |
| [Docs/REQUIREMENT.md](Docs/REQUIREMENT.md) | FR/NFR/AC 需求 |
| [Docs/M1-M4-backlog.md](Docs/M1-M4-backlog.md) | M1–M4 未闭环任务与执行顺序 |
| [Docs/M3-review.md](Docs/M3-review.md) | M3 独立复验与 P2/P3 收尾 |
| [Docs/PROMPT.md](Docs/PROMPT.md) | 逐阶段 Prompt/执行记录原文 |
| [openspec/](openspec/) | OpenSpec 主规格与归档 change |

## 5. 已知限制

- `search` 仅 mock，不访问真实搜索 API。
- LIVE 依赖 `.env` 的真实 Key；CI 默认 skip。
- Windows 下 POSIX `write_file` 有 1 个 skip；Linux 3.11 已单独验证。
- 覆盖率约 94.95%，低于 97% 目标。
- MySQL/Redis/Mongo 真机测试需 Docker；默认套件在未配置 env 时 skip。
