"""S21 手写轻量 DI 容器：工厂 + 单例/瞬时作用域。"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from agent_mini.config.models import AppConfig
from agent_mini.observability.errors import ConfigError


class Scope(StrEnum):
    """组件生命周期。"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class Service(StrEnum):
    """容器顶层服务键。"""

    CONFIG = "config"
    LLM = "llm"
    AGENT = "agent"
    APP = "app"


class Container:
    """无全局状态的轻量容器。"""

    def __init__(self) -> None:
        self._factories: dict[str, tuple[Callable[[], Any], Scope]] = {}
        self._singletons: dict[str, Any] = {}

    def register(
        self,
        key: str | Service,
        factory: Callable[[], Any],
        scope: Scope = Scope.SINGLETON,
    ) -> None:
        """注册工厂；重复注册覆盖旧注册。"""
        self._factories[str(key)] = (factory, scope)
        self._singletons.pop(str(key), None)

    def override(
        self,
        key: str | Service,
        factory: Callable[[], Any],
        scope: Scope | None = None,
    ) -> None:
        """测试替换入口；未指定作用域时保留原作用域。"""
        name = str(key)
        current = self._factories.get(name)
        self.register(name, factory, scope or (current[1] if current else Scope.SINGLETON))

    def resolve(self, key: str | Service) -> Any:
        """解析服务；工厂异常转为 ConfigError。"""
        name = str(key)
        if name not in self._factories:
            raise ConfigError(f"依赖未注册: {name}")
        factory, scope = self._factories[name]
        if scope is Scope.SINGLETON and name in self._singletons:
            return self._singletons[name]
        try:
            value = factory()
        except ConfigError:
            raise
        except Exception as exc:
            raise ConfigError(f"依赖构造失败: {name}") from exc
        if scope is Scope.SINGLETON:
            self._singletons[name] = value
        return value

    def build(self, key: str | Service = Service.APP) -> Any:
        """构建应用；失败传播 ConfigError。"""
        return self.resolve(key)


def build_container(config: AppConfig) -> Container:
    """装配顶层 LLM/Agent/HTTP app；内部组件仍显式构造。"""
    container = Container()
    container.register(Service.CONFIG, lambda: config, Scope.SINGLETON)
    container.register(Service.LLM, lambda: _build_llm(config), Scope.SINGLETON)
    container.register(Service.AGENT, lambda: _build_agent(container), Scope.TRANSIENT)
    container.register(Service.APP, lambda: _build_app(container), Scope.TRANSIENT)
    return container


def _build_llm(config: AppConfig) -> Any:
    from agent_mini.llm.client import HttpLLMClient
    from agent_mini.llm.models import ModelConfig as ClientConfig

    client_config = ClientConfig(
        base_url=config.model.base_url,
        model=config.model.model,
        timeout=config.model.timeout,
    )
    return HttpLLMClient(client_config, config.model.api_key.get_secret_value())


def _build_agent(container: Container) -> Any:
    from agent_mini.runtime.agent import Agent
    from agent_mini.runtime.registry_adapter import RegistryExecutor
    from agent_mini.tools import builtin as _builtin
    from agent_mini.tools.registry import DEFAULT_REGISTRY

    _ = _builtin
    return Agent(
        container.resolve(Service.LLM),
        tool_executor=RegistryExecutor(DEFAULT_REGISTRY),
    )


def _build_app(container: Container) -> Any:
    from agent_mini.interface.http import create_app

    return create_app(container.resolve(Service.AGENT))
