## Context

参见 `proposal.md`。S00 只需让包可安装、可导入、可查询版本，并让 pytest/ruff/mypy 可执行；后续业务模块不在本变更内。

## Goals / Non-Goals

**Goals:**

- 使用仓库根目录 `pyproject.toml` 作为唯一工程配置源。
- 让 `pip install -e .`、`pytest`、`ruff check`、`mypy agent_mini` 可直接运行。
- 版本号只维护一处，避免 `pyproject.toml` 与包代码重复。

**Non-Goals:**

- 不实现 LLM、Runtime、Tool、Memory、Context、HTTP、Observability、DI。
- 不引入运行时依赖。
- 不建立完整 CI 流水线。

## Decisions

- **构建后端选用 setuptools**：环境已有 setuptools，PEP 621 元数据可直接复用；不引入额外构建工具。
- **版本单一来源**：`agent_mini/__init__.py` 定义 `__version__`，`pyproject.toml` 通过动态版本读取该属性；避免双写漂移。
- **测试只覆盖 smoke**：TC-SMOKE-001 验证导入与版本查询，不提前测试后续模块。
- **配置集中在 pyproject**：pytest、ruff、mypy 段均放在 `pyproject.toml`，不新增分散配置文件。

## Risks / Trade-offs

- [动态版本读取依赖 setuptools 配置正确] → 用 `pip install -e .` 实际验证。
- [mypy strict 对空包也可能报配置问题] → 只检查 `agent_mini`，用实际 `mypy agent_mini` 验证。
- [ruff 规则集与旧版本不兼容] → 以本机 ruff 0.15.10 实测，必要时仅调整规则可用性，不降低已声明的可读性阈值。
