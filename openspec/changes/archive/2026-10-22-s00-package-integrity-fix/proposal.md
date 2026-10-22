## Why

S00 的 editable install 与源码目录检查已通过，但 wheel 未包含 `agent_mini/systemdb/schema.sql`，且缺少对“DESIGN §2.2 结构完整”和“占位模块只含 docstring”的自动检查。

## What Changes

- 在 `pyproject.toml` 为 `agent_mini.systemdb` 声明 `schema.sql` 的 package-data。
- 新增打包配置测试、DESIGN §2.2 文件清单测试、占位模块 AST 检查与 `schema.sql` 注释检查。
- 构建 wheel 并核对全部 35 个 `agent_mini/` 文件（含 2 个既有文件）。
- 将 S00 暂时回退为“进行中”，修正验收通过后恢复“已完成”。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `engineering-baseline`: 新增构建产物完整性与占位模块内容约束。

## Impact

- 修改 `pyproject.toml` 的 setuptools 配置；新增测试文件与测试用例。
- 不改变运行时行为、依赖清单或包版本。
