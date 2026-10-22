# Agent-mini

Agent-mini 是一个从零实现的最小 ReAct Agent。当前完成 S00 工程基线、S01 单轮模型接入、S02 错误分类/退避重试、S03 单轮直答与 S04 ReAct 工具循环；包含可安装包、OpenAI 兼容 LLM 客户端、`Agent.run(user_input)` 与 `ToolExecutor` 协议，不包含真实工具注册表、Memory、HTTP 接口或 S05 安全阀。

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

## 静态检查

```bash
ruff check .
ruff format --check .
mypy agent_mini tests
```
