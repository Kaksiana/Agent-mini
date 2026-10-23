# Agent-mini

Agent-mini 是一个从零实现的最小 ReAct Agent。当前完成 S00–S14：工程基线、单轮模型接入、错误分类/退避重试、单轮直答、ReAct 工具循环、安全阀、工具注册/Schema、calculator、time、todo、沙箱 read_file/write_file 与 search，以及 Redis 短时会话窗口；包含 `ToolRegistry`、pydantic Schema、`RegistryExecutor`、安全工具、未配置显式报错的 SearchProvider 与响应前同步写回，包含 MongoDB 中期存储；不包含 Context/HTTP 接口。

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





