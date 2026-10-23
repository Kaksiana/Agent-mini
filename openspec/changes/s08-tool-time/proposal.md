## Why

S08 需要按时区返回当前时间；S06 已有注册表，S07 已建立 calculator 风格。TC 使用 `tz`，本轮 Prompt 要求 `timezone`，需兼容并记录。

## What Changes

- 新增 `time_tool.py`：`TimeArgs(timezone: str | None)`、`@tool("time")`。
- 默认时区常量 `DEFAULT_TIMEZONE="Asia/Shanghai"`（S21 配置化前）。
- handler 接受 `timezone` 与兼容 `tz`，`timezone` 优先；支持 `now_provider` 注入。
- 非法/空/错误大小写时区返回 `invalid_timezone`；返回 ISO8601 + 时区名。
- 不实现其他工具/配置/沙箱。

## Capabilities

### New Capabilities

- `time-tool`: 时区感知当前时间。

## Impact

- 新增 time 工具与测试；更新 DESIGN/PLAN/TESTING/ISSUE/MEMORY/PROMPT/README/OpenSpec。
- 无新增依赖。
