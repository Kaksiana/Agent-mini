# Agent-mini

Agent-mini 是一个从零实现的最小 ReAct Agent。当前完成 S00–S20（HTTP API、结构化日志、统一异常）：工程基线、单轮模型接入、错误分类/退避重试、单轮直答、ReAct 工具循环、安全阀、工具注册/Schema、calculator、time、todo、沙箱 read_file/write_file 与 search，以及 Redis 短时会话窗口；包含 `ToolRegistry`、pydantic Schema、`RegistryExecutor`、安全工具、未配置显式报错的 SearchProvider 与响应前同步写回，包含 MongoDB、Context 裁剪、MySQL 系统库与 FastAPI HTTP 接口；不包含 S21 配置与 DI。

## 环境要求

- Python 3.11+

## 安装

```bash
pip install -e .
```

安装开发工具（pytest、pytest-asyncio、pytest-cov、respx、ruff、mypy）：

```bash
pip install -e ".[dev]"
```

## 版本查询

```bash
python -c "import agent_mini; print(agent_mini.get_version())"
```

## 测试

```bash
pytest
pytest -m unit
pytest -m contract
pytest --cov=agent_mini --cov-report=term-missing
```

## M1 离线演示

使用测试替身展示“直答 → 工具循环 → 安全阀”，不访问网络：

```bash
pytest -q \
  tests/unit/test_agent.py::test_direct_reply_returns_one_step_result \
  tests/unit/test_react_loop.py::test_two_step_tool_loop_pairs_messages \
  tests/unit/test_safety_valve.py::test_max_steps_stops_exactly_at_limit \
  tests/unit/test_safety_valve.py::test_deadline_cancels_hanging_tool_and_fills_batch
```

预期：`4 passed`。覆盖直接回复、两步工具配对、max_steps 固定文案与 deadline 取消/补齐。


## HTTP 服务

```bash
pip install -e ".[dev]"
cp .env.example .env
# 在环境中设置 DEEPSEEK_API_KEY，禁止写入 tracked 文件
uvicorn agent_mini.interface.http:create_app_from_env --factory --port 8000
curl http://127.0.0.1:8000/healthz
```

LIVE 验收：`RUN_LIVE=1 DEEPSEEK_API_KEY=... pytest -m live`；缺失时 skip。

## M3 离线演示

验证三轮记忆、跨轮上下文与超 K 整轮裁剪，不访问网络：

```bash
pytest -q tests/integration/test_m3_demo.py
```

预期：`1 passed`。覆盖三轮 StoredRound 只写当前轮、下一轮带历史、12 轮裁到最近 10 轮且 system/current 保留。
## M2 离线演示

验证六工具显式装载、文件往返与 search 未配置：

```bash
pytest -q tests/unit/test_m2_demo.py
```

预期：`2 passed`。覆盖干净进程加载 calculator/time/todo/read_file/write_file/search、write→read 往返、search `not_configured`。

## 静态检查

```bash
ruff check .
ruff format --check .
mypy agent_mini tests
```
