## Context

S08 报告 6 项：tzdata、Registry 类型、Schema 描述、固定时钟、ISSUE 时序、S07 归档后绕过 change。

## Decisions

- **tzdata**：`pyproject.toml` 增加 `tzdata>=2025.1; platform_system == "Windows"`；作为 zoneinfo 数据依赖，不引入 pytz/dateutil。
- **非字符串**：`TimeArgs` before validator 将非 None/非 str 转 `str`，handler 再判 invalid_timezone；Schema 仍为 string。
- **Schema 描述**：TimeArgs docstring 不再提 tz；测试对完整序列化 Schema 断言无 tz。
- **固定时钟**：断言完整 ISO 字符串；补 naive provider。
- **流程**：本 change 追溯 S07 修复；ISSUE-034 后补无法回改历史，记录例外，不再犯。
