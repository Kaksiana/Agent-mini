"""TC-L1-017/018：配置加载、脱敏与轻量 DI。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_mini.config.container import Container, Scope, build_container
from agent_mini.config.loader import load_config
from agent_mini.observability.errors import ConfigError

pytestmark = pytest.mark.unit

ENV = {
    "DEEPSEEK_API_KEY": "sk-config-sentinel",
    "MYSQL_DSN": "mysql+asyncmy://user:pass@localhost/db",
}


def _write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_explicit_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="不存在"):
        load_config(tmp_path / "missing.yaml", ENV)


def test_default_path_uses_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_config(environ=ENV)
    assert config.model.model == "deepseek-chat"
    assert config.model.api_key.get_secret_value() == ENV["DEEPSEEK_API_KEY"]
    assert config.systemdb.dsn.get_secret_value() == ENV["MYSQL_DSN"]
    assert "sk-config-sentinel" not in repr(config)
    assert "pass" not in repr(config.systemdb)


def test_missing_required_fields_raise_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
        load_config(environ={})
    with pytest.raises(ConfigError, match="MYSQL_DSN"):
        load_config(environ={"DEEPSEEK_API_KEY": "sk-x"})


def test_empty_key_and_bad_enum_raise_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
        load_config(environ={"DEEPSEEK_API_KEY": "   ", "MYSQL_DSN": "mysql://x"})
    path = _write_yaml(tmp_path / "config.yaml", "model:\n  provider: openai\n")
    with pytest.raises(ConfigError, match="provider"):
        load_config(path, ENV)


def test_env_overrides_yaml(tmp_path: Path) -> None:
    path = _write_yaml(
        tmp_path / "config.yaml",
        "model:\n  base_url: https://yaml.example\n  model: yaml-model\n"
        "tool:\n  max_file_size: 12\n",
    )
    config = load_config(path, {**ENV, "DEEPSEEK_BASE_URL": "https://env.example"})
    assert config.model.base_url == "https://env.example"
    assert config.model.model == "yaml-model"
    assert config.tool.max_file_size == 12


def test_config_is_frozen() -> None:
    config = load_config(environ=ENV)
    with pytest.raises(ValidationError):
        config.model.model = "changed"


def test_container_singleton_transient_and_override() -> None:
    container = Container()
    calls = {"count": 0}

    def singleton() -> object:
        calls["count"] += 1
        return object()

    container.register("single", singleton, Scope.SINGLETON)
    assert container.resolve("single") is container.resolve("single")
    assert calls["count"] == 1

    container.register("transient", object, Scope.TRANSIENT)
    assert container.resolve("transient") is not container.resolve("transient")

    fake = object()
    container.override("single", lambda: fake)
    assert container.resolve("single") is fake


def test_container_missing_and_failure_are_config_errors() -> None:
    container = Container()
    with pytest.raises(ConfigError, match="未注册"):
        container.build("missing")
    container.register("broken", lambda: 1 / 0, Scope.SINGLETON)
    with pytest.raises(ConfigError, match="broken"):
        container.resolve("broken")


def test_build_container_tops() -> None:
    config = load_config(environ=ENV)
    container = build_container(config)
    assert container.resolve("config") is config
    assert container.resolve("agent") is not container.resolve("agent")
