# DESIGN <!-- omit in toc -->

> **Agent-mini 设计文档**。规则见 `AGENT.md` §1（文档优先）与 §7（需求驱动开发）。
> 上位文档：`Docs/REQUIREMENT.md`（本文件所有设计点均可回溯到其中的 FR / NFR 编号）。

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.13（S03 复验修复：空白拒绝、字段不变量、调用链分层） |
| 日期 | 2026-10-22 |
| 状态 | 待评审 |
| 上游 | `Docs/REQUIREMENT.md` |
| 下游 | `Docs/TESTING.md`、`Docs/PLAN.md` |

---

## 1. 技术栈选型及理由

### 1.1 选型结论

| 领域 | 选型 | 版本约束 | 理由 |
| --- | --- | --- | --- |
| 语言 | Python | ≥ 3.11 | 异步语法成熟（`asyncio.TaskGroup`）、动态类型便于快速迭代 MVP、Redis/Mongo/MySQL/HTTP 客户端生态完整 |
| 运行时模型 | `asyncio` 单进程事件循环 | 内置 | Agent 主循环天然是 IO 密集（等模型、等工具、等存储），协程比线程更省资源 |
| HTTP 客户端 | `httpx` | ≥ 0.27 | 支持异步、超时/重试策略显式可配、`respx` 可在测试中拦截请求 |
| 数据模型与校验 | `pydantic` v2 + `pydantic-settings` | ≥ 2.6 | 配置与工具参数的 Schema 复用一套模型，校验错误信息可直接反馈给模型 |
| Web 框架 | `fastapi` + `uvicorn` | ≥ 0.110 | 与 pydantic 同源、自动生成 OpenAPI、异步原生；仅用于接口层，不侵入核心 |
| 短时记忆 | `redis`（redis-py 异步客户端） | ≥ 5.0 | 需求明确指定 Redis；TTL 与 List 结构天然适配会话窗口 |
| 中期记忆 | `pymongo`（官方异步 API） | ≥ 4.9 | 需求明确指定 MongoDB；文档模型适配消息记录，无需额外 ORM |
| 系统数据库 | `mysql` 8.x + `SQLAlchemy Core` + `asyncmy` | ≥ 2.0 / ≥ 0.2 | 需求明确指定 MySQL；承载**会话管理、系统模型、工具登记**与调用审计等系统信息，与 Redis/MongoDB 职责隔离 |
| Token 计数 | 本地 `tiktoken`（`cl100k_base`）+ 安全余量 | ≥ 0.7 | 纯本地估算，不依赖外部分发包与网络；可测试、可复现；与 DeepSeek 分词器的偏差由 10% 余量吸收 |
| 日志 | 标准库 `logging` + 自定义 JSON Formatter + `contextvars` | 内置 | 不引入 APM/日志框架，符合 NFR-OBS-01 且依赖最少 |
| 测试 | `pytest` + `pytest-asyncio` + `respx` + `fakeredis` + `mongomock` + `pytest-cov` | — | 覆盖单元、契约、集成四类；无外部依赖即可跑全量测试 |
| 属性测试 | `hypothesis` | — | 用于 calculator 与沙箱路径的组合爆炸场景 |
| 质量工具 | `ruff`（lint + format）+ `mypy` | — | 单工具替代 flake8/isort/black，配置集中 |
| 打包 | `pyproject.toml`（PEP 621） | — | 现代标准，`pip install -e .` 即可 |

### 1.2 备选方案与否决理由

| 备选 | 否决理由 |
| --- | --- |
| TypeScript / Node.js | 异步与生态同样成熟，但本项目大量逻辑是纯计算与数据结构操作（窗口裁剪、路径沙箱），Python 表达更短；且测试栈（pytest + hypothesis）对算法类代码覆盖更直接 |
| Go | 并发模型适合服务端，但 MVP 阶段迭代速度与表达力劣于 Python；HTTP SDK 与 Redis/Mongo/MySQL 客户端也更繁琐 |
| Java / Spring | 启动重、样板代码多，与"最小可用"目标背离 |
| 引入 LangChain 等 Agent 库 | **明确禁止**，见 `AGENT.md` §9 与本文 §6 |

### 1.3 依赖清单边界

- **允许**：通用基础库（HTTP、序列化、数据库驱动、Web 框架、测试工具）。
- **禁止**：任何提供 Agent 编排、ReAct 循环、工具调用调度、记忆管理能力的框架（清单见 §6）。
- 新增依赖必须在 PR 描述中说明理由，并确认不在禁止清单内。

## 2. 总体架构

### 2.1 分层视图

```
┌───────────────────────────────────────────────────────────┐
│                交互接口层 Interface（仅 HTTP）               │
│                      FastAPI / uvicorn                     │
└───────────────────────────┬───────────────────────────────┘
                            │ AgentRequest{session_id, input}
┌───────────────────────────▼───────────────────────────────┐
│                   Agent Runtime（ReAct 主循环）              │
│    build context → call LLM → 判定 → 执行工具 → 再判定 → 收敛  │
└──────┬────────────────────┬───────────────────┬───────────┘
       │                    │                   │
┌──────▼──────┐   ┌─────────▼────────┐  ┌───────▼──────────┐
│ Context 管线 │   │  Tool 能力层      │  │  Memory 记忆      │
│ 拼接+token预算│   │ registry + 6 tools│  │ Redis 短时        │
│ +轮次窗口     │   │ Sandbox          │  │ Mongo 中期        │
└──────┬──────┘   └─────────┬────────┘  └───────┬──────────┘
       │                    │                   │
┌──────▼────────────────────▼───────────────────▼──────────┐
│                    模型接入层 LLM                          │
│        OpenAI Chat Completions 协议 → DeepSeek             │
└───────────────────────────────────────────────────────────┘

┌─────────────┐   ┌───────────────────── 横切关注点 ────────────────────┐
│ SystemDB    │   │  Observability（JSON 日志 / trace_id / 异常分类）    │
│ MySQL 8     │   │  Config & DI（模型配置 / 工具配置 / Prompt 配置）    │
│ 会话管理     │   └──────────────────────────────────────────────────────┘
│ 模型/工具登记 │
│ 调用审计     │
└─────────────┘
```

**三类存储职责严格隔离**（详见 §3.9）：

| 存储 | 存什么 | 不存什么 |
| --- | --- | --- |
| Redis | 当前会话的消息窗口（List + TTL） | 历史正文、审计 |
| MongoDB | 对话消息正文（可跨会话检索） | 系统元数据、审计 |
| MySQL | 会话管理、系统模型、工具登记、调用审计、请求指标 | 任何对话正文 |

### 2.2 代码目录结构

```
agent_mini/
├── __init__.py
├── config/            # 配置模型 + DI 容器
│   ├── models.py      # ModelConfig / ToolConfig / PromptConfig / SystemDBConfig
│   ├── loader.py      # 文件 + 环境变量加载与校验
│   └── container.py   # 依赖注入容器
├── llm/               # 模型接入层
│   ├── client.py      # LLMClient（httpx）
│   ├── models.py      # LLMRequest / LLMResponse / Usage
│   └── errors.py      # 超时、限流、鉴权、服务端错误
├── runtime/           # Agent Runtime（ReAct）
│   ├── agent.py       # Agent.run 入口
│   ├── loop.py        # 主循环 + 安全阀
│   └── result.py      # AgentResult / ToolCallTrace
├── tools/             # Tool 能力层
│   ├── registry.py    # ToolSpec / ToolRegistry / @tool 装饰器
│   ├── sandbox.py     # 路径解析与越界校验
│   └── builtin/       # calculator / time / todo / read_file / write_file / search
├── memory/            # Memory
│   ├── short_term.py  # Redis
│   ├── mid_term.py    # MongoDB
│   └── base.py        # Protocol 定义
├── context/           # Context 管线
│   ├── builder.py     # 管线拼接
│   ├── token_counter.py # 本地 tokenizer 估算（tiktoken + 余量）
│   └── window.py      # 双触发整轮裁剪
├── systemdb/          # 系统数据库（MySQL）
│   ├── schema.sql     # 建表 DDL
│   ├── repository.py  # sessions / models / tools / tool_invocations / request_metrics
│   └── models.py
├── interface/         # 交互入口（仅 HTTP）
│   └── http.py
└── observability/     # 可观测与治理
    ├── logging.py     # JSON Formatter + trace context
    └── errors.py      # 异常分类与错误码
```

> **占位规范**：除 `__init__.py` 与 `version.py` 外，S00 骨架文件仅允许模块级中文 docstring；`schema.sql` 仅允许注释。占位文件不得 import 第三方库或本包子模块，不得包含函数、类或业务逻辑；对应阶段实现时再补实现。非 Python 文件通过 `package-data` 进入 wheel。

## 3. 各模块设计要点

### 3.1 模型接入层

- **核心接口**

  ```python
  class LLMClient(Protocol):
      async def chat(self, messages: list[Message], tools: list[ToolSchema] | None = None, **params) -> LLMResponse: ...
  ```

- **协议**：`POST {base_url}/chat/completions`，请求体遵循 OpenAI 规范（`model`、`messages`、`tools`、`tool_choice`、`temperature`、`max_tokens`）。
- **响应归一**：`LLMResponse(content: str | None, reasoning_content: str | None, tool_calls: list[ToolCall], usage: Usage, finish_reason)`；缺失或 null 的 `tool_calls` 归一为空列表。`reasoning_content` 缺失或 null 均合法，不通过正则从普通正文猜测推理字段。
- **工具参数解析**：先校验整个响应的结构和调用 ID（非空且本轮内唯一），再对每个 `function.arguments` 严格 JSON 反序列化，拒绝重复键、NaN/Infinity 与非 object 顶层；工具名、参数 Schema 由注册表校验。JSON/Schema 错误返回对应 call_id 的 `ToolResult`，不执行该工具，允许模型读错后修正；不使用 `eval` 或代码块提取兜底。
- **模式配置**：首版默认显式发送 `thinking={"type":"disabled"}`；可配置开启思考模式，开启后按供应商协议保留 `reasoning_content`，实际模型名通过配置指定，不写死旧型号。
- **协议依据（2026-10-21 核对）**：DeepSeek 的 `reasoning_content` 与 `content` 是独立字段；思考模式下携带 `tools` 的后续请求，需要回传所保留历史的推理字段，包括未调用工具的历史 assistant 消息。仅对当前保留的完整轮次回传，不复活已裁剪历史。见 [官方思考模式](https://api-docs.deepseek.com/guides/thinking_mode/) 与 [官方工具调用](https://api-docs.deepseek.com/guides/tool_calls/)。
- **错误解析边界**：无 choices、空 choices、message 类型不合法、tool_calls 结构不合法或调用 ID 重复，抛 `LLMProtocolError`（`LLM_PROTOCOL_ERROR/502`），本响应的任何工具均不执行。原始响应仅用于内存解析，默认不落盘、不记日志；诊断只输出脱敏的错误类型与 trace_id。
- **S01 实现边界**：客户端只负责请求、归一与判别；非法工具参数以 `ToolCall.error_code="invalid_arguments"` 保留 call_id，Runtime/ToolResult 映射在 S04/S06；HTTP 状态分类与重试在 S02。S01 临时 `ModelConfig`（base_url/model/timeout）位于 `llm/models.py`，S21 配置层迁移或复用。
- **协议硬化（S01 评估修复）**：响应顶层必须是 JSON object，否则统一抛 `LLMProtocolError`；`model/thinking` 等受控字段不得由 `**params` 覆盖；`reasoning_content` 仅允许 assistant 消息携带。异常类统一使用 `*Error` 后缀。
- **错误与重试（S02）**：`400 → LLMBadRequestError`、`401/403 → LLMAuthError`、`429 → LLMRateLimitError`、`5xx → LLMServerError`、超时 `→ LLMTimeoutError`、其他传输异常 `→ LLMConnectionError`。仅 429/5xx 重试，最多 3 次总请求；退避 `0.5 * 2^(attempt-1)` 秒并叠加 `[0, 0.1]` 秒抖动；4xx、超时、协议错误不重试。客户端默认把每次重试写入 `retry_events` 快照，`on_retry` 仅用于外部订阅。
- **错误处理**：`401/403` → `LLMAuthError`；`429` 与 `5xx` → 指数退避重试（默认 3 次，底数 0.5s，带抖动）；`400` → `LLMBadRequestError`（不重试）；超时 → `LLMTimeoutError`（不重试，交由 Runtime 收敛）。
- **无状态**：不持有会话；调用方传入完整 `messages`。

### 3.2 Agent Runtime

#### 3.2.0 S03 单轮直答接口

S03 只实现无工具的单轮闭环；构造器注入 `LLMClient`，不读取环境变量，不在内部实例化客户端。

| 项目 | S03 契约 |
| --- | --- |
| 构造器 | `Agent(llm_client: LLMClient)` |
| 运行签名 | `async def run(self, user_input: str) -> AgentResult` |
| 会话参数 | `session_id` 延后到 S13；S03 不接收会话 ID |
| 消息 | 仅发送一条 `user` 消息 |
| 成功 | 无 tool_calls 且 `content` 非空时返回一步结果 |

**AgentResult（S03）**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `reply` | `str` | 仅最终回复文本，不混入 reasoning/trace |
| `steps` | `int` | LLM 调用步数；S03 直答为 1 |
| `usage` | `Usage` | 本轮所有 LLM 调用 usage 之和，不二次归一化 |
| `trace` | `tuple[ThoughtStep, ...]` | 每次 LLM 响应一条；S04 新增 |
| `tool_calls` | `int` | 本轮工具调用总次数；S04 新增 |
| `tool_traces` | `tuple[ToolCallTrace, ...]` | 展平的公开工具记录；S04 新增 |

`AgentResult` MUST 为冻结模型，禁止下游静默修改。`truncated` 延后 S05，`session_id` 延后 S13；`reply` 语义保持不变（仅最终文本）。

**异常契约**：`LLMError` 及其子类必须原样向调用方传播，不吞、不包装。S04 有 `ToolExecutor` 时，tool_calls 进入工具循环；无 executor 且上游返回 tool_calls 视为请求契约违反，仍抛 `LLMProtocolError`；响应结构非法同样只由 `LLMProtocolError` 表示。content 为 `None`、空字符串或纯空白且无 tool_calls 时抛 `LLMEmptyResponseError`。

#### 3.2.1 调用链

**S03 当前链路**

```
user_input
 └─ Agent.run(user_input)
     ├─ LLMClient.chat([user])
     └─ 无 tool_calls 且 content 非空白
         └─ AgentResult(reply, steps=1, usage)
```

**最终目标链路（S04+，按阶段落地）**

```
HTTP handler
 └─ Agent.run(session_id, user_input)              # S13 增加 session_id
     ├─ 1. SystemDB.ensure_session(session_id)     # S13
     ├─ 2. ContextBuilder.build(...)               # S07+
     ├─ 3. ReAct 循环（上限 max_steps）             # S04；安全阀 S05
     │     ├─ 3.1 Context.fit(messages, tools)     # S07+
     │     ├─ 3.2 LLMClient.chat(messages, tools)
     │     ├─ 3.3 tool_calls → ToolRegistry.execute / 消息配对
     │     └─ 3.4 每次响应记录 ThoughtStep         # S04
     ├─ 4. Memory 写回（时机见 3.2.2）              # S13
     └─ 5. SystemDB.record_metrics(...)            # S17
 └─ HTTP response {reply, steps, tool_calls, usage, trace, trace_id}
```

#### 3.2.2 Memory 写回时机与调用链

| 存储 | 写回时机 | 方式 | 失败影响 |
| --- | --- | --- | --- |
| Redis 短时 | 本轮最终回复确定后、**响应返回前** | 同步 `await` | 降级：记录 `memory.degraded` 告警，仍返回响应 |
| MongoDB 中期 | 响应返回后 | 异步任务（不阻塞响应） | 仅告警，不影响本轮响应 |
| MySQL 审计/指标 | 响应返回后 | 异步批量 | 仅告警（`systemdb.degraded`） |

**顺序保证**：`AgentResult` 生成 → **同步**写 Redis（保证下一轮可读）→ 构造并返回 HTTP 响应 → **异步**写 Mongo 与 MySQL。禁止先返回响应再写 Redis，否则下一轮可能读不到上一轮。

**写入内容**：按"轮"写入——`user` 消息 + 本轮所有 `assistant` / `tool` 往返 + 最终 `assistant` 回复，与 Context 的"轮"定义一致，避免裁剪时错位。

**中断情形**：循环被安全阀中断（`truncated=true`）时，先为本批未完成的调用补齐同 call_id 的结构化取消/超时结果，再写回合法配对的完整轮次，并标记 truncated。不可裁剪内容仍超预算的例外见 §3.5，该轮不进入可恢复窗口。

#### 3.2.3 思考过程解析与决策轨迹（Thought Process）

区分两类数据：模型实际返回的 `reasoning_content` 是可选协议字段；面向用户的 `thought` 是运行时根据可观察动作生成的简短决策摘要。运行时摘要不是模型原始推理，也不从最终答案反推“思考”。普通 `content` 单独保留，按 §3.2.4 决定是否为最终答案。

每次 LLM 响应产出一条 `ThoughtStep`，失败响应也记录步骤与错误码；多工具调用按顺序记录在同一条 trace 内：

| 字段 | 含义 | 说明 |
| --- | --- | --- |
| `step` | Runtime 调用 LLMClient.chat 的序号（从 1 开始） | 与日志 step 一致；trace 条数等于调用次数，客户端内部 HTTP 重试只记 attempt，不增加步骤 |
| `decision` | `tool_call / final / error` | 由响应判别表产生 |
| `thought` | 如“调用 calculator 获取结果”“返回最终答案” | 仅描述可观察行为，不复制完整模型推理或最终文本 |
| `thought_source` | 固定为 `runtime_summary` | 明确摘要来源，禁止标记为模型原始思考 |
| `reasoning_present` | 是否解析到非空 `reasoning_content` | 无推理字段不算错误，也不伪造内容 |
| `tool_calls` | `tuple[ToolCallTrace, ...]` | 元素为 `{call_id, tool, args, ok, error_code, observation}`；参数按白名单脱敏，结果摘要先脱敏再截断至 200 字符 |
| `error_code` | 可选的步骤错误码 | final 步骤的 tool_calls 为空列表 |

- HTTP `trace` 与 `event=react.step` 日志仅使用上述公开字段，`AgentResult.tool_calls` 仅表示调用总次数；`tool_traces` 是所有步骤的工具调用记录展平结果。
- 原始 `reasoning_content` 不出现在 HTTP、日志、MySQL、搜索召回片段或公开 trace；不额外请求模型生成推理。思考模式启用且携带 tools 时，仅作为同一 session 的私有协议状态随原 assistant 消息保存在 Redis/Mongo，按完整轮次保留/裁剪，并计入实际请求 token；跨会话不可读。非思考模式不主动收集该字段。
- `content` 在有 tool_calls 时是伴随文本，不能提前作为最终回复；无 tool_calls 时才可被判定为最终答案。工具结果以 tool 消息回灌，公开 trace 摘要不再注入上下文，避免重复和污染。

#### 3.2.4 主循环伪代码

```
tools_snapshot = registry.schemas()           # 本轮冻结实际发送的工具 Schema
messages = context.build(...)                 # 完整消息 + 必需的私有协议字段
trace = []
for step in 1..max_steps:
    messages = context.fit(messages, tools_snapshot)  # 超预算抛 ContextTooLarge，不发请求
    resp = llm.chat(messages, tools=tools_snapshot)
    decision = parse_decision(resp)            # 先检查 finish_reason 与结构，再决定分支
    if decision == final:
        messages.append(assistant(content=resp.content, private_reasoning=resp.reasoning_content))
        trace.append(final_step(step, reasoning_present=bool(resp.reasoning_content)))
        return AgentResult(reply=resp.content, steps=step, trace=trace)
    messages.append(assistant(content=resp.content, tool_calls=resp.tool_calls,
                              private_reasoning=resp.reasoning_content))
    calls_trace = []
    for call in resp.tool_calls:
        result = registry.execute_or_error(call)  # 含 JSON/Schema/未知工具的结构化错误
        messages.append(tool(call_id=call.id, content=result.to_content()))
        calls_trace.append(public_tool_trace(call, result))
    trace.append(tool_step(step, calls_trace, reasoning_present=bool(resp.reasoning_content)))
    if repeated_signature(messages) exceeds threshold: break   # 死循环检测
return AgentResult(reply=fallback_message, steps=len(trace), truncated=True, trace=trace)
```

- **工具结果的消息格式**：必须成对写入 `assistant(tool_calls)` 与 `tool(tool_call_id)`，否则模型会报协议错误（对应 FR-RT-04）。
- **安全阀**：`max_steps`（默认 8）、`deadline`（默认 120s）、`repeat_threshold`（同一 `(name,args)` 连续 3 次即中断）。这些参数与 `truncated` 在 S05 接入；S04 循环只负责工具往返与正常收敛，不实现强制终止。
- **终止语义**：正常收敛返回模型内容；触达安全阀返回明确提示并标记 `truncated=True`（对应 FR-RT-05、AC-10）。

响应判别表按自上而下优先级执行；终止错误交给统一错误处理，已发生的工具调用不会回滚或自动重放：

| 条件 | 判定与处理 | 工具副作用 |
| --- | --- | --- |
| 响应结构或 ID 不合法 | `LLM_PROTOCOL_ERROR/502` | 本响应不执行工具 |
| `finish_reason=length` | `LLM_OUTPUT_TRUNCATED/502`，不把截断正文当最终答案 | 本响应不执行工具 |
| `finish_reason=content_filter` 或未知终止原因 | `LLM_OUTPUT_REJECTED/502` 或 `LLM_PROTOCOL_ERROR/502` | 本响应不执行工具 |
| 非空 tool_calls，finish_reason 为 tool_calls 或 stop | `decision=tool_call`，即使 content 同时存在也先执行工具 | 结构校验后按序执行；参数错误仅回灌错误结果 |
| tool_calls 为空、finish_reason=stop、content 去空白后非空 | `decision=final`，保留原始 content | 无 |
| 仅 reasoning_content、空白 content，或 tool_calls 终止却无调用 | `LLM_EMPTY_RESPONSE/502` 或 `LLM_PROTOCOL_ERROR/502` | 无；不无限重试 |

### 3.3 Tool 能力层

- **S04 最小 Protocol**：`runtime/loop.py` 定义 `ToolExecutor`（`schemas() -> list[ToolSchema]`、`async execute(ToolCall) -> ToolOutcome`）与 `ToolOutcome(ok, content, error_code)`。S04 只接受测试替身；S06 的注册表实现该协议，不把注册实现放入 runtime。
- **注册机制**：`@tool(name, description, params_model, enabled_key)` 装饰器写入全局 `ToolRegistry`；启动时由配置决定启停；`ToolSpec.to_json_schema()` 由 pydantic 模型生成，保证模型侧与服务侧 Schema 同源（FR-TOOL-01）。
- **执行契约**：`handler(**validated_args) -> ToolResult`；**所有异常必须被捕获并转为** `ToolResult(ok=False, error_code=..., content=可读说明)`，不得向上抛出（FR-RT-06）。
- **可信会话上下文**：注册表以 `ToolContext(session_id, trace_id)` 向 todo 等状态工具注入会话信息；session_id 不放入模型可写参数 Schema，若模型伪造该参数则按额外字段拒绝。模型不能自行指定另一个会话的待办分区。
- **沙箱**：`Sandbox(root).resolve(rel_path)` 执行四步校验——① 拒绝绝对路径；② 拼接后 `Path.resolve()` 求真实路径；③ 校验真实路径仍在 `root` 之下（防 `..` 与符号链接逃逸）；④ 校验大小与扩展名白名单。任何一步失败抛 `SandboxViolation`（FR-TOOL-07）。
- **六个工具**

  | 工具 | 实现要点 | 风险控制 |
  | --- | --- | --- |
  | calculator | `ast.parse` 白名单节点（`BinOp/UnaryOp/Constant` 等），自行求值 | 禁止 `eval/exec/import`；除零与溢出归一为错误（FR-TOOL-02） |
  | time | `datetime.now(ZoneInfo(tz))`，默认取配置时区 | 非法时区返回参数错误（FR-TOOL-03） |
  | todo | 以会话为键的列表，存储复用 Memory 的 KV 能力 | 空列表返回空集合；不跨会话（FR-TOOL-04） |
  | read_file | 读文本，限制体积与编码 | 越界阻断、二进制拒绝（FR-TOOL-05） |
  | write_file | 写文本，默认不覆盖已有文件（需显式 `overwrite`） | 越界阻断、大小上限、原子写（临时文件 + `os.replace`）（FR-TOOL-06） |
  | search | `SearchProvider` 协议 + `NullProvider`（未配置时返回 `not_configured`） | **禁止伪造搜索结果**（FR-TOOL-08） |

### 3.4 Memory 记忆

- **抽象**：`ShortTermStore` / `MidTermStore` 两个 Protocol，实现可替换（测试用 fakeredis / mongomock）。
- **短时（Redis）**：`session:{id}:messages` 为 List，每个元素是一个完整轮次 `{round_id, messages[]}`，一次 RPUSH 写入一轮；按整轮 LTRIM 保留最近 K 轮（默认 10），EXPIRE 默认 24h。读取后展开轮内消息，禁止按默认 50 条消息截断而拆散工具往返。
- **中期（MongoDB）**：集合 `messages`，字段 `{session_id, round_id, role, content, tool_calls, tool_call_id, reasoning_content?, created_at}`；索引 `(session_id, created_at desc)`。`reasoning_content` 是受 session 限定的私有协议字段，不进入关键词检索或公开输出；上下文恢复完整轮次时才按模式加载。普通检索按 session 过滤、时间倒序和可选 content 关键词执行。
- **降级**：任一存储不可用时记录 `memory.degraded` 告警日志并返回空集合，上层继续运行（FR-MEM-05、AC-07）。
- **写回时机**：Redis 在响应前同步 await，Mongo 在响应后异步写回；失败告警，详见 §3.2.2。公开 trace 摘要不作为历史消息重复存储。
- **边界重申**：Memory **不存**会话元数据与审计（属 MySQL），也**不**做轮次窗口裁剪（属 Context）。

### 3.5 Context 管线与压缩

- **组装顺序**：`system prompt（配置）→ 工具摘要（可选）→ 中期记忆摘要 → 短时窗口消息（时间正序）→ 当前用户消息`。
- **工具定义位置**：实际工具定义由 `registry.schemas()` 生成，作为请求体顶层 `tools` 独立发送，不能只统计可选的工具摘要。Context 接收该次请求的 `tools_snapshot`；计数和 HTTP 发送复用同一份快照，启停变化从下一用户请求生效。
- **Token 计算（本地估算）**：
  - **实现**：`LocalTokenCounter.count_request(messages, tools)` 基于 `tiktoken` 的 `cl100k_base`；对实际 messages 与非空 tools 分别做规范 JSON 序列化（`ensure_ascii=False, sort_keys=True, separators=(",", ":")`），计数后叠加集中配置的 `protocol_overhead_tokens`（默认保守预留 256）。覆盖 role、content、tool_calls 的 ID/名称/参数、tool_call_id、工具结果、实际回传的 reasoning_content，以及工具名称、描述、完整 parameters Schema（嵌套 properties、required、enum、$defs/$ref 等）。无 tools 时该项为 0；工具摘要若也发送，则作为 messages 的一部分正常计数。
  - **公式**：`estimated_input_tokens = message_tokens + tool_schema_tokens + protocol_overhead_tokens`；messages 与 tools 都为空时总计为 0。`tool_schema_tokens` 对整个实际 tools 数组计数，不逐字段重复累加，也不重复计算已在 messages 内的历史 tool_calls。
  - **定位**：纯本地估算，**不依赖任何外部 tokenizer 包分发或在线接口**；不下载官方离线包，也不调用服务端做预估。
  - **安全余量**：因 `cl100k_base` 与 DeepSeek 分词器并非同一套，预算计算统一保留 **10% 余量**以吸收偏差。
  - **预算** = `model.max_context_tokens` − `max_output_tokens`（默认 1024）− **安全余量 10%**。
  - **每次出站前**调用 `Context.fit`：首次拼接、每批工具结果回灌后及裁剪后都重新统计实际请求，比较 `estimated_input_tokens ≤ budget`。响应 `usage` 仅用于观测对账，不参与预算判断。本地 tokenizer 与供应商不同源，10% 余量降低超限风险，不宣称数学上保证服务端 token 永不超限。
  - **降级**：`tiktoken` 不可用时对同样的规范 JSON 文本退回字符比例估算（ASCII 约 0.3、非 ASCII 约 0.6 token/字符，各项向上取整），保留结构开销与 10% 余量，并记录 `token_counter.degraded`。
- **压缩策略 = 双触发的整轮滑动窗口**：
  - 「一轮」= 一条 `user` 消息 + 其后的 `assistant` 回复 + 其间所有 `assistant(tool_calls)/tool` 往返，作为**不可拆分的整体**；
  - **触发条件（任一成立）**：轮次数 > K（默认 10） **或** 估算 token > 预算；
  - **动作**：从**最旧的一轮整轮丢弃**，丢弃后重新计数，直到两个条件同时满足；
  - **绝不**拆分或截断单条消息，也绝不丢弃 system prompt 与当前用户消息。
- **边界情形**：system、实际 tools 与当前轮（含所有已产生的工具往返）不可删减；完整历史轮次全部裁掉后仍超预算，记录 `context.over_budget_after_trim`，本地抛 `ContextTooLarge`（`CONTEXT_TOO_LARGE/400`），不再调用 LLM。若前面已执行工具，错误响应带脱敏 trace、steps 和 `truncated=true`，且不自动重试产生重复副作用；单轮过大拒绝写入可恢复窗口，仅保留脱敏审计。远端因估算偏差返回超限 400 时按 `LLMBadRequestError/502` 明确返回。
- **可追溯**：`ContextPayload` 记录 `rounds_before / rounds_after / dropped_rounds / tokens_before / tokens_after / message_tokens / tool_schema_tokens / protocol_overhead_tokens / budget / trim_reason(rounds|tokens|both)`，并写入日志 `event=context.trimmed`（FR-CTX-04）；tokens_before/after 都指完整请求估算值。token 紧张时“保留最近 K 轮”表示最多 K 个已完成历史轮次，可能少于 K；当前轮不计入历史轮次窗口。

### 3.6 交互接口层

- **仅 HTTP**，不提供 CLI / REPL / 图形界面（NG-03、G-06）：
  - `POST /chat`：`{session_id?, message}` → `{session_id, reply, steps, tool_calls, usage, trace, trace_id, truncated}`；`tool_calls` 是整数，trace 结构见 §3.2.3；未触发安全阀时 truncated=false。
  - `GET /healthz`：返回依赖连通性（Redis / Mongo / MySQL），**不暴露密钥**。
- **会话**：请求未带 `session_id` 时由服务生成（UUID4）并在响应中返回；带则复用。
- **错误码**：`400` 入参非法、`408` 超时、`429` 上游限流、`502` 模型不可用、`500` 内部错误（FR-IF-04）。
- **无状态服务**：进程内不缓存会话，全部状态落 Redis / Mongo / MySQL，便于重启后继续。

### 3.7 可观测与治理

- **日志**：JSON 行，字段固定 `ts/level/event/trace_id/session_id/step/duration_ms`；`trace_id` 通过 `contextvars` 注入，跨异步边界保持。
- **异常体系**：`AgentError` 基类 → `ConfigError / LLMError / ToolError / SandboxError / ContextError / InputError / SystemDBError`，每个带 `code` 与 `http_status`。S02–S19 的 `LLMError` 暂时作为独立临时根，S20 统一接入 `AgentError`；具体类型统一 `*Error` 后缀，临时根到期后必须迁移。
- **脱敏**：日志过滤器统一拦截 `api_key`、`authorization`、`password` 字段（NFR-SEC-02、AC-14）。

### 3.8 配置与依赖注入

- **配置分层**：`config.yaml`（非敏感）+ 环境变量（敏感项：`DEEPSEEK_API_KEY`、`REDIS_URL`、`MONGO_URI`、`MYSQL_DSN`）。DeepSeek 密钥统一使用 `DEEPSEEK_API_KEY`，禁止 `LLM_API_KEY` 别名（ISSUE-013）。
- **四类配置**：`ModelConfig`（provider/base_url/model/timeout/retry）、`ToolConfig`（启停、sandbox_root、max_file_size、search provider）、`PromptConfig`（system prompt 文件路径 + 窗口轮次）、`SystemDBConfig`（DSN、连接池、是否自动建表）。
- **校验**：`pydantic-settings` 启动即校验，缺失必填项直接失败并给出字段名（FR-CFG-01、AC-13）。
- **DI 容器**：轻量手写容器（注册工厂 + 单例/瞬时作用域），按配置装配 `LLMClient`、`ToolRegistry`、`Memory`、`ContextBuilder`、`SystemDB`、`Agent`；测试可注入替身（FR-CFG-04）。

### 3.9 系统数据库（MySQL）

- **定位**：存放**系统自身运行所需的信息**，与 Redis（短时消息窗口）、MongoDB（对话正文）**互不影响、互不替代**。
- **表设计**

  | 表 | 关键字段 | 用途 |
  | --- | --- | --- |
  | `sessions` | `session_id`(PK)、`status`(active/idle/closed)、`created_at`、`last_active_at`、`message_count`、`meta`(JSON) | 会话管理：登记、活跃度、状态流转 |
  | `models` | `id`、`name`(UK)、`provider`、`base_url`、`model`、`max_context_tokens`、`enabled`、`created_at`、`updated_at` | 系统模型登记：可用模型与上下文上限 |
  | `tools` | `id`、`name`(UK)、`version`、`description`、`params_schema`(JSON)、`enabled`、`created_at`、`updated_at` | 工具登记：名称、描述、参数 Schema、启停 |
  | `tool_invocations` | `id`、`session_id`、`trace_id`、`tool_name`、`ok`、`error_code`、`duration_ms`、`created_at` | 工具调用审计 |
  | `request_metrics` | `id`、`trace_id`、`session_id`、`steps`、`tool_calls`、`prompt_tokens`、`completion_tokens`、`duration_ms`、`created_at` | 请求级指标落库 |

- **写入时机**：启动时把配置中的模型与工具登记信息幂等 upsert 到 `models` / `tools`；会话首次出现及每轮结束更新 `sessions`；每轮结束异步写 `tool_invocations`；请求结束异步写 `request_metrics`。
- **隔离约束**：**不得**把对话正文写入 MySQL；**不得**把系统信息与审计写入 Redis/Mongo。三库任何一方不可用都不应影响另外两方。
- **降级**：MySQL 不可用时对话主链路照常返回，仅系统信息与审计丢失，并记录 `systemdb.degraded` 告警（不阻断，与 FR-MEM-05 的降级策略一致）。
- **初始化**：`systemdb/schema.sql` 为幂等 DDL；`SystemDBConfig.auto_create=true` 时启动执行，生产环境建议关闭并走手工迁移。
- **驱动**：`SQLAlchemy Core` + `asyncmy`（异步、参数化查询，不引入 ORM，避免额外抽象）。

## 4. 模块间依赖关系

### 4.1 允许的依赖方向

| 模块 | 允许依赖 | 禁止依赖 |
| --- | --- | --- |
| 交互接口层 | Runtime、SystemDB、Config、Observability | Tool 内部实现、LLM 细节 |
| Runtime | LLM、Tool、Memory、Context、SystemDB、Observability | Interface、具体存储驱动 |
| Context | Memory（读）、Config、Observability | LLM 请求实现、Tool 执行 |
| Tool | Config、Observability、Sandbox | Runtime、Memory、Interface |
| Memory | Config、Observability | Runtime、Tool、Interface |
| SystemDB | Config、Observability | Runtime、Tool、Memory、Interface |
| LLM | Config、Observability | 任何上层模块 |
| Config | 无（仅标准库 + pydantic） | 其余全部业务模块 |
| Observability | 无（仅标准库） | 其余全部业务模块 |

**硬约束**：依赖只能单向指向下层；`Config`、`Observability`、`SystemDB` 为叶子模块，不得反向依赖任何业务模块（NFR-MAINT-02）。

### 4.2 依赖矩阵（✓ = 允许）

| ↓依赖者 / 被依赖→ | Config | Obs | LLM | Tool | Memory | Context | SystemDB | Runtime | Interface |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Config | — | | | | | | | | |
| Observability | | — | | | | | | | |
| LLM | ✓ | ✓ | — | | | | | | |
| Tool | ✓ | ✓ | | — | | | | | |
| Memory | ✓ | ✓ | | | — | | | | |
| Context | ✓ | ✓ | | | ✓ | — | | | |
| SystemDB | ✓ | ✓ | | | | | — | | |
| Runtime | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | |
| Interface | ✓ | ✓ | | | | | ✓ | ✓ | — |

## 5. 关键数据流

### 5.1 单轮直答（UC-01 / UC-11）

```
Client → POST /chat → Interface
  → SystemDB.ensure_session(session_id)
  → ContextBuilder.build()        # 读 Memory → 拼接 → 计 token → 双触发裁剪
  → LLMClient.chat(messages, tools)
  → 无 tool_calls
  → AgentResult(reply, steps, usage)        # S03；trace 等 S04/S05，session_id S13
  → Memory.write_back_short_term()          # 同步，响应返回前
  → 200 {session_id, reply, steps=1, usage, trace, trace_id}
  → [异步] Memory.write_back_mid_term() + SystemDB.record_metrics()
```

### 5.2 工具调用循环（UC-02/03/04）

```
第 1 步: messages → LLM → tool_calls=[calculator("2+2")]
         messages += assistant(tool_calls)
         registry.execute → ToolResult("4")
         messages += tool(call_id, "4")
         SystemDB.record_tool_invocation(...)
第 2 步: messages → LLM → content="结果是 4"，无 tool_calls
         → 收敛，steps=2
```

### 5.3 按轮次滑动窗口裁剪（UC-09）

```
build: 历史 14 轮 / tokens = 21000，K = 10，预算 = 16000
  → 第 1 次裁剪（触发原因 rounds）：整轮丢弃最旧 4 轮 → 10 轮
  → 重新计数：tokens = 17200 仍 > 16000
  → 第 2 次裁剪（触发原因 tokens）：再整轮丢弃 2 轮 → 8 轮，tokens = 15100
  → 保留 system prompt + 最近 8 轮 + 当前消息
  → payload{rounds_before=14, rounds_after=8, dropped_rounds=6,
            tokens_before=21000, tokens_after=15100, trim_reason=both}
  → 日志 event=context.trimmed
```

### 5.4 记忆与系统库写入

```
AgentResult →
  ├─ [响应前·同步] Redis:  RPUSH 完整轮次 + LTRIM(最近 K 轮) + EXPIRE(24h)
  ├─ [响应后·异步] Mongo:  insert_many（对话正文，失败仅告警）
  └─ [响应后·异步] MySQL:  UPSERT sessions / INSERT tool_invocations、request_metrics（失败仅告警）
```

## 6. 不依赖现有 Agent 框架的说明

### 6.1 明确禁止引入

| 类别 | 禁止项 |
| --- | --- |
| Agent 编排 / 图执行 | **langgraph**、**openhands**、**openclaw**、**PI** |
| 同类 Agent 框架 | LangChain、LlamaIndex、AutoGen、CrewAI、Semantic Kernel、smolagents、Dify SDK 等提供 Agent 循环 / 工具调度 / 记忆管理能力的库 |
| 托管 Agent 平台 | 任何以 API 形式代管 Agent 循环与工具调用的云服务 |

### 6.2 自研范围（不得外包）

| 能力 | 自研实现位置 | 说明 |
| --- | --- | --- |
| ReAct 主循环 | `runtime/loop.py` | 自行实现"判断 → 调工具 → 读结果 → 再判断"的控制流 |
| 工具注册与调度 | `tools/registry.py` | 自行实现注册表、Schema 生成、参数校验与调用分发 |
| 消息协议拼装 | `runtime/agent.py` | 自行维护 `assistant/tool` 消息配对 |
| 记忆读写 | `memory/*` | 仅使用数据库驱动，不借助记忆框架 |
| 上下文窗口裁剪 | `context/window.py` | 自研按轮次滑动窗口算法 |

### 6.3 允许使用的底层能力

`httpx`（HTTP）、`pydantic`（校验）、`redis`/`pymongo`/`asyncmy`（存储驱动）、`fastapi`（Web 框架）、`tiktoken`（本地分词计数）、`pytest`（测试）。这些是**通用基础库**，不包含 Agent 语义，不构成对 Agent 框架的依赖。

### 6.4 合规验证方式

1. `pyproject.toml` 的 `dependencies` 逐项人工评审并记录在 PR 描述中。
2. 依赖清单中不得出现 §6.1 列出的包名（含间接依赖）。
3. 代码评审时检查 `runtime/`、`tools/` 中不存在对第三方 Agent 编排能力的调用。
4. 对应验收项：`AC-18`。

## 7. 关键设计决策与权衡

| 编号 | 决策 | 理由 | 代价 / 风险 | 替代方案 |
| --- | --- | --- | --- | --- |
| ADR-001 | 采用**原生 function calling**（`tools` 参数）而非文本解析 ReAct | 协议层保证参数结构化，避免正则解析歧义；DeepSeek 兼容 OpenAI 协议 | 强依赖模型支持 tool calling；换模型需确认兼容性 | 文本 ReAct（`Thought/Action: ...`），易解析但脆弱 |
| ADR-002 | Python 3.11 + asyncio | 迭代快、IO 密集场景协程高效、测试生态成熟 | GIL 限制 CPU 密集场景（本项目无此需求） | Node.js / Go |
| ADR-003 | 中期记忆**不引入向量库** | 符合 NG-02；减少部署复杂度；MVP 用时间 + 关键词已足够 | 语义召回能力弱 | 引入 FAISS/Qdrant + embedding |
| ADR-004 | 配置与 DI **最后交付**，前期先用环境变量直读 | 遵循需求给定的开发顺序；避免过早抽象 | 前期代码存在临时读取点，第 8 阶段需一次重构 | 先做 DI 再做业务 |
| ADR-005 | 上下文**同时**受 token 预算与轮次窗口约束，裁剪仍按**整轮丢弃** | 既保证不超模型上限，又保持"轮"语义完整、不产生孤立 `tool` 消息 | 引入 tokenizer 依赖；两次计数带来少量开销 | 仅按 token 裁剪（会拆消息）/ 仅按轮次（可能超限） |
| ADR-006 | 沙箱用 **root + realpath 校验**，不用容器/进程隔离 | 实现简单、跨平台、无额外运行时依赖 | 无法防御 CPU/内存耗尽类攻击（非目标） | 子进程 + seccomp / 容器 |
| ADR-007 | 日志用标准库 + JSON Formatter | 零依赖、满足 NFR-OBS-01 | 无采样、无远程汇聚 | structlog / OpenTelemetry |
| ADR-008 | 引入 **MySQL 作为系统数据库**，与 Redis/MongoDB 职责隔离 | 需求要求；系统元数据与审计需要事务与结构化查询，Redis/Mongo 不适合承担 | 多一套需运维的存储；增加连接与迁移成本 | 复用 MongoDB 存元数据 |
| ADR-009 | 搜索用 **Provider 协议 + NullProvider** | 未配置时显式报错，杜绝伪造结果 | 首版开箱无真实搜索能力 | 内置某家搜索 SDK（带来密钥与网络依赖） |
| ADR-010 | HTTP 用 FastAPI | 与 pydantic 同源、OpenAPI 免费、异步原生 | 引入 uvicorn 运行时 | 标准库 `http.server`（能力太弱） |
| ADR-011 | **只提供 HTTP 入口**，不实现 CLI | 符合 NG-03 与 G-06；减少一套入口的测试与维护成本 | 本地调试需起服务或写脚本 | 同时提供 CLI |
| ADR-012 | MySQL 访问用 `SQLAlchemy Core` + `asyncmy`，不引入 ORM | Core 足够表达五张表；避免 ORM 抽象与 N+1 | 手写 SQL 与映射 | SQLModel / Tortoise ORM |
| ADR-013 | MySQL 扩为**系统信息库**（会话管理 / 系统模型 / 工具登记 / 审计指标） | 需求要求；这些数据需要事务、唯一约束与联表统计，Redis/Mongo 不适合 | 表结构需随功能演进迁移 | 仅存审计，模型与工具仅放配置文件 |
| ADR-014 | 公开 trace 仅展示带来源标记的运行时决策摘要；模型 reasoning 作为可选私有协议字段 | 区分解析与展示，不伪造模型思考；思考工具模式仍满足供应商回传要求 | 需保护 session 内私有字段并参与完整请求计数 | 直接把正文或推理原文记入公开 trace |
| ADR-015 | Token 计数用**本地 `tiktoken` 估算 + 10% 安全余量** | 不依赖外部分发包与网络；可测试、可复现；实现与运维成本最低 | 与 DeepSeek 分词器不同源，存在系统偏差，靠余量吸收 | 官方离线 tokenizer（需分发官方包，已放弃）/ 纯字符比例（更粗） |

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| DeepSeek 与 OpenAI 协议存在细微差异 | 工具调用解析失败 | 契约测试覆盖真实响应结构与可选 reasoning；仅记录脱敏错误元数据 |
| Redis / Mongo / MySQL 本地不可用 | 集成测试无法跑 | 单元测试用 fakeredis/mongomock/内存替身；集成测试标记 `@integration`，无依赖时跳过并记录 |
| 按轮次裁剪时拆散了工具往返 | 出现 `tool` 消息无对应 `tool_calls` 的协议错误 | 以"轮"为不可分割单位整体丢弃；用例覆盖含工具调用的轮次 |
| 工具被注入恶意参数 | 越权访问文件 | 沙箱四步校验 + 属性测试覆盖路径组合 |
| MySQL 写入阻塞主链路 | 响应变慢 | 异步批量写 + 不可用时降级为仅告警 |
| 配置层最后交付导致重构面大 | 第 8 阶段风险集中 | 前期所有外部依赖通过构造函数注入，第 8 阶段仅集中装配 |
| token 估算与 DeepSeek 分词器存在系统偏差 | 预估值偏离真实用量 | 统一保留 10% 安全余量；`usage` 落库用于对账；超限按 `LLMBadRequestError` 明确报错 |
| 整轮裁剪后仍超预算（单轮或 Schema 过大） | 请求无法发送 | 本地返回 CONTEXT_TOO_LARGE，不丢弃必要 Schema，不再发送超预算请求 |

## 9. 本次修订验证与回滚

- 影响范围：LLM 归一化、Runtime 判别与 trace、Memory 轮次边界、Context 计数输入、HTTP 响应字段；均为实现前设计修订。
- 文档验收：新增测试编号与需求/计划关联一致；公开 trace 不含原始 reasoning；每次出站的计数和工具快照一致；真实 API 用例有独立执行门禁。
- 回滚方式：若评审否决，按本次 Git diff 局部撤回定义与对应映射，保留 Prompt/Issue 历史；不涉及任何数据库初始化或数据迁移。

---

## 10. 变更记录

| 版本 | 日期 | 变更 | 影响范围 |
| --- | --- | --- | --- |
| v0.6 | 2026-10-21 | 解析契约、完整请求预算与验收用例修订 | 全文 |
| v0.7 | 2026-10-22 | 环境变量统一为 `DEEPSEEK_API_KEY`，移除 `LLM_API_KEY` 别名 | §3.8；联动 `Docs/ISSUE.md` ISSUE-013、`openspec/specs/engineering-standards/spec.md` C-02 |
| v0.8 | 2026-10-22 | 澄清 S01 客户端/错误/临时 ModelConfig/非法工具参数边界 | §3.1；联动 ISSUE-020 |
| v0.9 | 2026-10-22 | 协议硬化：非 object 顶层、保留字段、reasoning 角色；异常临时根说明 | §3.1、§3.7；联动 S01-report、ISSUE-022 |
| v0.10 | 2026-10-22 | S02 错误分类与退避重试：状态码/httpx 异常映射、3 次尝试、抖动与不重试边界 | §3.1；联动 TC-L2-004/005/006 |
| v0.11 | 2026-10-22 | 重试策略硬上限 1–3、RetryEvent、cap 后非递减、3xx 归协议错误；临时异常根 S20 到期 | §3.1、§3.7；联动 S02-report、ISSUE-026 |
| v0.12 | 2026-10-22 | S03 单轮直答：`AgentResult.reply/steps/usage`、`Agent.run(user_input)`、构造器注入；session_id 延后 S13 | §3.2；联动 ISSUE-028、TC-L1-015A/B/C |
| v0.13 | 2026-10-22 | S03 复验：拒绝空白 reply、AgentResult 不变量、§5.1 final→reply、调用链分层 | §3.2、§5.1；联动 S03-report P1/P2 |
| v0.14 | 2026-10-22 | S04 ReAct 循环：AgentResult 增量字段、ToolExecutor Protocol、LLMProtocolError 语义收敛、S05 安全阀边界 | §3.2、§3.3、§3.7；联动 ISSUE-029、TC-L1-015/024/028/030、TC-L2-009/010、TC-L3-006 |
