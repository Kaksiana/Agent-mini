## Context

配置读取集中在 HTTP 的 os.environ；容器仅装配顶层服务。

## Decisions

- 用 pydantic-settings 读取 env，PyYAML 读取 config.yaml；env 优先。
- 四类配置冻结；SecretStr 包裹 key/dsn/url。
- 默认值集中在 models.py；必填 DEEPSEEK_API_KEY、MYSQL_DSN。
- Container：config/llm singleton；agent/app transient；override 不改业务代码。
- ISSUE-025 选 (a)：httpx<0.29、pydantic<3、pytest<9。
