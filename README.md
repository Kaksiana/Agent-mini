# Agent-mini

Agent-mini 是一个从零实现的最小 ReAct Agent。当前处于 S00 工程基线阶段，仅提供可安装的包骨架，不包含模型接入、Runtime、工具、记忆或接口功能。

## 环境要求

- Python 3.11+

## 安装

```bash
pip install -e .
```

安装开发工具（pytest、ruff、mypy）：

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
```

## 静态检查

```bash
ruff check .
ruff format --check .
mypy agent_mini
```
