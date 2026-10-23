## Why

S08 报告发现 Windows 全新安装无 tzdata、非字符串时区在 Registry 误判、Schema 描述暴露 tz、固定时钟断言不足；同时 S07 归档后修复未建 change。该 change 追溯记录并固化 S07/S08 边界。

## What Changes

- 声明 Windows `tzdata>=2025.1` 运行依赖；wheel 元数据必须包含。
- `TimeArgs` 在 before validator 将非字符串转为字符串，使 Registry 路径最终返回 `invalid_timezone`。
- 从 TimeArgs 模型描述移除 `tz`；完整 Schema 断言不含未支持别名。
- 固定时钟断言完整 ISO8601；增加 naive provider。
- 新 change 追溯覆盖 S07 Registry 超长边界；记录 ISSUE-034 后补的流程例外。

## Capabilities

### Modified Capabilities

- `calculator`: Registry 超长错误码一致性。
- `time-tool`: Registry 类型、Schema 描述、确定性时钟与 Windows 数据依赖。

## Impact

- `pyproject.toml`、`time_tool.py`、S07/S08 测试与文档；无新第三方时区逻辑库。
