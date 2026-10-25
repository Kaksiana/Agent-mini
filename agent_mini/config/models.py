"""S21 四类冻结配置模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 60.0
DEFAULT_RETRIES = 2
DEFAULT_SANDBOX_ROOT = Path("./workspace")
DEFAULT_MAX_FILE_SIZE = 1024 * 1024
DEFAULT_SEARCH_PROVIDER: Literal["none", "mock"] = "none"
DEFAULT_PROMPT_PATH = Path("./prompts/system.md")
DEFAULT_WINDOW_ROUNDS = 10
DEFAULT_POOL_SIZE = 5
DEFAULT_POOL_TIMEOUT = 2.0


class _Frozen(BaseModel):
    """禁止未知字段与运行期修改。"""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelConfig(_Frozen):
    """模型配置；api_key 使用 SecretStr。"""

    provider: Literal["deepseek"] = "deepseek"
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    retry: int = Field(default=DEFAULT_RETRIES, ge=1, le=3)
    api_key: SecretStr

    @field_validator("base_url", "model")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("不能为空")
        return value

    @field_validator("api_key")
    @classmethod
    def _key_not_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("DEEPSEEK_API_KEY 不能为空")
        return value


class ToolConfig(_Frozen):
    """工具启停、沙箱与搜索配置。"""

    enabled: bool = True
    sandbox_root: Path = DEFAULT_SANDBOX_ROOT
    max_file_size: int = Field(default=DEFAULT_MAX_FILE_SIZE, gt=0)
    search_provider: Literal["none", "mock"] = DEFAULT_SEARCH_PROVIDER


class PromptConfig(_Frozen):
    """系统提示词与窗口轮次。"""

    system_prompt_path: Path = DEFAULT_PROMPT_PATH
    window_rounds: int = Field(default=DEFAULT_WINDOW_ROUNDS, ge=1, le=100)


class SystemDBConfig(_Frozen):
    """系统库 DSN、连接池与建表开关。"""

    dsn: SecretStr
    pool_size: int = Field(default=DEFAULT_POOL_SIZE, ge=1, le=100)
    pool_timeout_seconds: float = Field(default=DEFAULT_POOL_TIMEOUT, gt=0)
    auto_create: bool = False

    @field_validator("dsn")
    @classmethod
    def _dsn_not_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("MYSQL_DSN 不能为空")
        return value


class AppConfig(_Frozen):
    """应用级配置聚合。"""

    model: ModelConfig
    tool: ToolConfig = ToolConfig()
    prompt: PromptConfig = PromptConfig()
    systemdb: SystemDBConfig
    redis_url: SecretStr | None = None
    mongo_uri: SecretStr | None = None
    version: int = 1
