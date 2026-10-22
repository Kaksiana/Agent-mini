# Agent-mini

Agent-mini 是一个从零实现的最小 ReAct Agent。当前完成 S00 工程基线、S01 单轮模型接入与 S02 错误分类/退避重试；包含可安装包与 OpenAI 兼容 LLM 客户端，不包含 Runtime、工具、记忆或接口功能。

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
mypy agent_mini
```
