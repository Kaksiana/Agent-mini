# Agent-mini 真机测试执行结果

> 执行时间：2026-10-25 17:20–17:30（Asia/Shanghai）  
> 执行基线：`bd0b714`（docs: add real-machine demo test cases）  
> 环境：Windows + Docker Desktop；Python 3.13.9；真实 DeepSeek；MySQL 8 / Redis 7 / Mongo 7  
> 密钥：来自 `.env`，仅在测试进程内读取；本文未输出 Key 值。  
> 执行人：当前 Agent（自动化 + HTTP 真机请求）

## 1. 环境确认

| 项目 | 结果 |
| --- | --- |
| `.env` 存在 | 是 |
| `DEEPSEEK_API_KEY` 已配置 | 是（值未输出） |
| `.env` 中 `RUN_LIVE` | 未配置为 1；本次命令显式 `RUN_LIVE=1` |
| `agent-mini-mysql` | Up，`0.0.0.0:3307->3306` |
| `agent-mini-redis` | Up，`0.0.0.0:6380->6379` |
| `agent-mini-mongo` | Up，`0.0.0.0:27018->27017` |

## 2. 总结

| 套件/场景 | 结果 | 状态 |
| --- | --- | --- |
| Docker + LIVE 全量 pytest | **395 passed, 1 skipped** | PASS |
| LIVE 独立执行 | **3 passed** | PASS |
| MySQL 8 系统库 | **8 passed** | PASS |
| Redis/Mongo/ContextBuilder 真实链路 | **3 passed** | PASS |
| M3 五文件 | **54 passed** | PASS |
| Python 3.11 全量 | **394 passed, 2 skipped** | PASS |
| wheel + 仓库外导入 | 成功 | PASS |
| HTTP `/healthz` | 200，三依赖 ok | PASS |
| HTTP `/chat` 真实模型 + calculator | 200，`reply=4`，steps=2，tool_calls=1 | PASS |
| HTTP 空 session | 400 `INVALID_INPUT` | PASS |

P0 演示项全部通过；skip 为已知平台/环境门控。

## 3. 全量真机 pytest

### 命令

```bash
export MYSQL_TEST_DSN='mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini'
export REDIS_TEST_URL='redis://127.0.0.1:6380/0'
export MONGO_TEST_URI='mongodb://127.0.0.1:27018'
export RUN_LIVE=1
pytest -q
```

### 结果

```text
........................................................................ [ 36%]
........................................................................ [ 54%]
........................................................................ [ 72%]
........................................................................ [ 90%]
..........................s.........                                     [100%]

SKIPPED [1] tests/unit/test_write_file.py:131: POSIX dir_fd path only
395 passed, 1 skipped in 24.64s
```

### 处理结果

- 真实 MySQL、Redis、Mongo、LIVE 用例均执行。
- 唯一 skip 为 Windows 下 POSIX-only `write_file`；Docker Python 3.11 已单独验证。
- 完整原始输出保存在本地 `.test-full.log`。

## 4. LIVE 独立执行

### 命令

```bash
RUN_LIVE=1 pytest tests/live -q
```

### 结果

```text
...                                                                      [100%]
3 passed in 4.17s
```

### 覆盖

| 用例 | 结果 | 关键断言 |
| --- | --- | --- |
| LIVE-001 直答 | PASS | `1+1` 回复含 `2`，usage>0，Key 不出现 |
| LIVE-002 工具闭环 | PASS | 真实 calculator、tool_traces ok、trace_id 非空 |
| LIVE-003 thinking | PASS | thinking 调用成功，回复含 `9`，Key 不出现 |

## 5. HTTP 真机请求

### 5.1 启动

```bash
export MYSQL_DSN='mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini'
export REDIS_URL='redis://127.0.0.1:6380/0'
export MONGO_URI='mongodb://127.0.0.1:27018'
export MYSQL_AUTO_CREATE=true
python -c "from agent_mini.interface.server import main; main()"
```

服务监听 `127.0.0.1:8000`。

### 5.2 `GET /healthz`

**响应**：HTTP 200

```json
{"status":"ok","dependencies":{"redis":"ok","mongo":"ok","mysql":"ok"}}
```

**处理结果**：三项 Docker 依赖均通过真实 ping/查询。

### 5.3 `POST /chat`（真实模型 + calculator）

**请求**

```json
{"session_id":"demo-result","message":"请只回答：2+2 等于几？"}
```

**响应**：HTTP 200

```json
{
  "session_id": "demo-result",
  "reply": "4",
  "steps": 2,
  "tool_calls": 1,
  "usage": {
    "prompt_tokens": 1907,
    "completion_tokens": 39,
    "total_tokens": 1946
  },
  "trace": [
    {
      "step": 1,
      "decision": "tool_call",
      "thought": "调用工具 calculator",
      "thought_source": "runtime_summary",
      "reasoning_present": false,
      "tool_calls": [
        {
          "call_id": "call_00_aZuYDIHC6MidThXws6qb2408",
          "tool": "calculator",
          "args": {"expression": "2+2"},
          "ok": true,
          "error_code": null,
          "observation": "4"
        }
      ],
      "error_code": null
    },
    {
      "step": 2,
      "decision": "final",
      "thought": "返回最终答案",
      "thought_source": "runtime_summary",
      "reasoning_present": false,
      "tool_calls": [],
      "error_code": null
    }
  ],
  "trace_id": "0c5e734e7dd24ea29ebaef736e5ff340",
  "truncated": false
}
```

**处理结果**：

- 模型真实调用成功；
- 模型选择 calculator，参数 `{"expression":"2+2"}`；
- 工具执行成功，observation=`4`；
- 最终 reply=`4`；
- steps=2、tool_calls=1；
- reasoning_present=false，未公开 reasoning；
- trace_id 非空且响应一致。

### 5.4 空 `session_id`

**请求**

```json
{"session_id":"   ","message":"hi"}
```

**响应**：HTTP 400

```json
{
  "code": "INVALID_INPUT",
  "message": "请求参数不合法",
  "trace_id": "c3d52b90b86141609e472596c16cd8f6"
}
```

**处理结果**：Pydantic 校验拦截，未进入 Agent，未返回 500。

## 6. 工具级真机结果

以下为直接通过 `ToolRegistry.execute` 在真实进程内执行，使用临时沙箱目录。

### calculator

```json
{"ok":true,"content":"4","error_code":null}
{"ok":false,"content":"除数不能为零","error_code":"division_by_zero"}
```

### time

```json
{"ok":true,"content":"2026-10-25T17:23:15.255834+08:00 Asia/Shanghai","error_code":null}
```

### todo 全生命周期

```json
{"ok":true,"content":"{\"items\": [{\"id\": 1, \"content\": \"buy milk\", \"status\": \"open\"}]}","error_code":null}
{"ok":true,"content":"{\"items\": [{\"id\": 1, \"content\": \"buy milk\", \"status\": \"done\"}]}","error_code":null}
{"ok":true,"content":"{\"items\": [{\"id\": 1, \"content\": \"buy milk\", \"status\": \"done\"}]}","error_code":null}
{"ok":true,"content":"{\"items\": []}","error_code":null}
```

**处理结果**：add → complete(index=1) → list → delete(index=1) → list 全部成功；错误字段名 `content` 不用于 complete/delete，需用 `index`。

### write_file / read_file

```json
{"ok":true,"content":"{\"path\": \"out.txt\", \"size\": 4, \"overwritten\": false}","error_code":null}
{"ok":true,"content":"{\"content\": \"demo\", \"size\": 4, \"encoding\": \"utf-8\"}","error_code":null}
```

### 沙箱逃逸

```json
{"ok":false,"content":"不允许上级目录","error_code":"path_escape"}
```

### search mock

```json
{
  "ok": true,
  "content": "{\"provider\": \"mock\", \"truncated\": false, \"results\": [{\"title\": \"Mock result for agent-mini demo\", \"url\": \"https://example.invalid/mock\", \"snippet\": \"mock provider; no network access\", \"source\": \"mock\"}]}",
  "error_code": null
}
```

**处理结果**：mock provider 生效，URL 为 `.invalid`，无真实网络访问。

## 7. Docker 依赖与跨版本

| 测试 | 命令/环境 | 结果 |
| --- | --- | --- |
| MySQL 8 | `MYSQL_TEST_DSN=... pytest tests/integration/test_systemdb.py -q` | 8 passed |
| Redis/Mongo 往返 | `REDIS_TEST_URL=... MONGO_TEST_URI=... pytest tests/integration/test_real_services.py -q` | 3 passed |
| M3 | 五文件 pytest | 54 passed |
| Python 3.11 | `python:3.11-slim` + 三服务 + LIVE，`pytest -q` | 394 passed, 2 skipped |
| wheel | `python -m build --wheel` + `pip install --target <temp>` + 仓库外 import | 成功 |

Python 3.11 两个 skip：容器内无 `git`、POSIX Windows seam。

## 8. DEMO 用例执行映射

| 用例 | 状态 | 证据 |
| --- | --- | --- |
| DEMO-001 health | PASS | 5.2 |
| DEMO-002 MySQL 审计 | PASS | 全量 + MySQL 8 |
| DEMO-003 calculator | PASS | 5.3、6 |
| DEMO-004 time | PASS | 6 |
| DEMO-005 todo | PASS | 6 |
| DEMO-006 read_file | PASS | 6 |
| DEMO-007 write_file | PASS | 6 |
| DEMO-008 路径逃逸 | PASS | 6 |
| DEMO-009 防覆盖 | PASS（自动化） | `test_write_file` |
| DEMO-010 search mock | PASS | 6 |
| DEMO-011 search none | PASS（自动化） | `test_search_provider_mock_and_none` |
| DEMO-012 跨轮记忆 | PASS | 真实 Redis/Mongo + 全量 |
| DEMO-013 ContextTooLarge | PASS（自动化） | `test_context_too_large_keeps_evidence` |
| DEMO-014 14 轮裁剪 | PASS（自动化） | `test_context_window` |
| DEMO-015 HTTP 错误映射 | PASS | 5.4 + 全量 |
| DEMO-016 LIVE 直答 | PASS | 4 |
| DEMO-017 LIVE 工具 | PASS | 4 |
| DEMO-018 LIVE thinking | PASS | 4 |

## 9. 失败/跳过与限制

| 项 | 说明 |
| --- | --- |
| Windows POSIX write_file | 1 skip；Linux Python 3.11 已 22 passed、1 skip |
| Python 3.11 容器 git | 1 skip（`git` 不存在） |
| search | 仅 mock，不宣称真实搜索 |
| LIVE 模型 | 使用 `.env` 当前 Key；模型版本 `deepseek-chat` |
| 覆盖率 | 94.95%，低于 97% |
| 人工逐条留证 | 本报告为自动化 + HTTP/工具探测；DEMO-009/011/013/014 为自动化映射，未单独截图 |

## 10. 结论

- P0 演示链路通过：health、真实模型、calculator、MySQL 审计、LIVE。
- 工具级 calculator/time/todo/read/write/search mock/沙箱逃逸均有真实进程输出。
- Redis/Mongo/MySQL 三依赖真实连通。
- 唯一 skip 为平台/环境已知项。
- **本次真机测试通过，可用于项目演示；search 真实能力不在本阶段范围。**
