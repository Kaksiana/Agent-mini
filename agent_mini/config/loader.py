"""S21 配置加载：YAML 非敏感 + 环境变量覆盖。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_mini.config.models import (
    AppConfig,
    ModelConfig,
    PromptConfig,
    SystemDBConfig,
    ToolConfig,
)
from agent_mini.observability.errors import ConfigError

DEFAULT_CONFIG_PATH = Path("config.yaml")
FIELD_HINTS = {"model.api_key": "DEEPSEEK_API_KEY", "systemdb.dsn": "MYSQL_DSN"}


class _Env(BaseSettings):
    """只声明受支持的环境变量；未知变量忽略。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: SecretStr | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    base_url: str | None = Field(default=None, alias="DEEPSEEK_BASE_URL")
    model: str | None = Field(default=None, alias="DEEPSEEK_MODEL")
    timeout: float | None = Field(default=None, alias="DEEPSEEK_TIMEOUT")
    retry: int | None = Field(default=None, alias="DEEPSEEK_RETRY")
    redis_url: SecretStr | None = Field(default=None, alias="REDIS_URL")
    mongo_uri: SecretStr | None = Field(default=None, alias="MONGO_URI")
    mysql_dsn: SecretStr | None = Field(default=None, alias="MYSQL_DSN")
    system_pool_size: int | None = Field(default=None, alias="MYSQL_POOL_SIZE")
    system_pool_timeout: float | None = Field(default=None, alias="MYSQL_POOL_TIMEOUT")
    system_auto_create: bool | None = Field(default=None, alias="MYSQL_AUTO_CREATE")
    sandbox_root: Path | None = Field(default=None, alias="SANDBOX_ROOT")
    search_provider: str | None = Field(default=None, alias="SEARCH_PROVIDER")
    prompt_path: Path | None = Field(default=None, alias="SYSTEM_PROMPT_PATH")
    window_rounds: int | None = Field(default=None, alias="WINDOW_ROUNDS")


def load_config(
    path: str | Path | None = None,
    environ: dict[str, str] | None = None,
) -> AppConfig:
    """加载并校验配置；任何缺失/非法均抛 ConfigError。"""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if config_path.exists():
        data = _read_yaml(config_path)
    elif path is not None:
        raise ConfigError(f"配置文件不存在: {config_path}")

    source = environ if environ is not None else os.environ
    if environ is not None:
        missing = _missing_mapping(environ)
        if missing:
            raise ConfigError(f"配置缺失: {', '.join(missing)}")
    try:
        env = cast(Any, _Env)(**dict(source))
    except ValidationError as exc:
        names = []
        for error in exc.errors():
            name = ".".join(str(part) for part in error["loc"])
            names.append(FIELD_HINTS.get(name, name))
        raise ConfigError(f"配置校验失败: {', '.join(names)}") from exc
    missing = _missing_required(env)
    if missing:
        raise ConfigError(f"配置缺失: {', '.join(missing)}")
    for section in ("model", "tool", "prompt", "systemdb"):
        value = data.get(section)
        if value is not None and not isinstance(value, dict):
            raise ConfigError(f"配置校验失败: {section} 必须是映射")
    model_data = dict(data.get("model") or {})
    system_data = dict(data.get("systemdb") or {})
    _apply_model_env(model_data, env)
    _apply_system_env(system_data, env)
    model_data["api_key"] = env.api_key
    system_data["dsn"] = env.mysql_dsn
    data["model"] = model_data
    data["systemdb"] = system_data
    data["tool"] = _merge_tool(data.get("tool"), env)
    data["prompt"] = _merge_prompt(data.get("prompt"), env)
    if env.redis_url is not None:
        data["redis_url"] = env.redis_url
    if env.mongo_uri is not None:
        data["mongo_uri"] = env.mongo_uri
    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        fields = []
        for error in exc.errors():
            name = ".".join(str(part) for part in error["loc"])
            fields.append(FIELD_HINTS.get(name, name))
        raise ConfigError(f"配置校验失败: {', '.join(fields)}") from exc


def _missing_mapping(values: dict[str, str]) -> list[str]:
    missing = []
    for name in ("DEEPSEEK_API_KEY", "MYSQL_DSN"):
        if not values.get(name, "").strip():
            missing.append(name)
    return missing


def _missing_required(env: _Env) -> list[str]:
    missing = []
    if env.api_key is None or not env.api_key.get_secret_value().strip():
        missing.append("DEEPSEEK_API_KEY")
    if env.mysql_dsn is None or not env.mysql_dsn.get_secret_value().strip():
        missing.append("MYSQL_DSN")
    return missing


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"配置文件不可读: {path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml 顶层必须是映射")
    return raw


def _apply_model_env(data: dict[str, Any], env: _Env) -> None:
    if env.base_url is not None:
        data["base_url"] = env.base_url
    if env.model is not None:
        data["model"] = env.model
    if env.timeout is not None:
        data["timeout"] = env.timeout
    if env.retry is not None:
        data["retry"] = env.retry


def _apply_system_env(data: dict[str, Any], env: _Env) -> None:
    if env.system_pool_size is not None:
        data["pool_size"] = env.system_pool_size
    if env.system_pool_timeout is not None:
        data["pool_timeout_seconds"] = env.system_pool_timeout
    if env.system_auto_create is not None:
        data["auto_create"] = env.system_auto_create


def _merge_tool(data: object, env: _Env) -> dict[str, Any]:
    merged = dict(data) if isinstance(data, dict) else {}
    if env.sandbox_root is not None:
        merged["sandbox_root"] = env.sandbox_root
    if env.search_provider is not None:
        merged["search_provider"] = env.search_provider
    return merged


def _merge_prompt(data: object, env: _Env) -> dict[str, Any]:
    merged = dict(data) if isinstance(data, dict) else {}
    if env.prompt_path is not None:
        merged["system_prompt_path"] = env.prompt_path
    if env.window_rounds is not None:
        merged["window_rounds"] = env.window_rounds
    return merged


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "ModelConfig",
    "PromptConfig",
    "SystemDBConfig",
    "ToolConfig",
    "load_config",
]
