"""S21 手写轻量 DI 容器：工厂 + 单例/瞬时作用域。"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from agent_mini.config.models import AppConfig
from agent_mini.observability.errors import ConfigError

DEFAULT_CONTEXT_TOKENS = 32_000


class Scope(StrEnum):
    """组件生命周期。"""

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class Service(StrEnum):
    """容器顶层服务键。"""

    CONFIG = "config"
    LLM = "llm"
    SHORT_TERM = "short_term"
    MID_TERM = "mid_term"
    SYSTEM_DB = "system_db"
    CONTEXT = "context"
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
    container.register(Service.SHORT_TERM, lambda: _build_short_term(config), Scope.SINGLETON)
    container.register(Service.MID_TERM, lambda: _build_mid_term(config), Scope.SINGLETON)
    container.register(Service.SYSTEM_DB, lambda: _build_system_db(config), Scope.SINGLETON)
    container.register(Service.CONTEXT, lambda: _build_context(config), Scope.SINGLETON)
    container.register(Service.AGENT, lambda: _build_agent(container), Scope.TRANSIENT)
    container.register(Service.APP, lambda: _build_app(container), Scope.TRANSIENT)
    return container


def _build_llm(config: AppConfig) -> Any:
    from agent_mini.llm.client import HttpLLMClient, RetryPolicy
    from agent_mini.llm.models import ModelConfig as ClientConfig

    client_config = ClientConfig(
        base_url=config.model.base_url,
        model=config.model.model,
        timeout=config.model.timeout,
    )
    retry = RetryPolicy(max_attempts=config.model.retry)
    return HttpLLMClient(
        client_config,
        config.model.api_key.get_secret_value(),
        retry=retry,
    )


def _build_agent(container: Container) -> Any:
    from agent_mini.runtime.agent import Agent
    from agent_mini.runtime.registry_adapter import RegistryExecutor
    from agent_mini.tools import builtin as _builtin
    from agent_mini.tools.registry import DEFAULT_REGISTRY, ToolContext, ToolRegistry

    _ = _builtin
    config = container.resolve(Service.CONFIG)
    from agent_mini.tools.builtin.search import (
        MockProvider,
        configure_search_provider,
        reset_search_provider,
    )

    if config.tool.search_provider == "mock":
        configure_search_provider(MockProvider())
    else:
        reset_search_provider()
    registry = DEFAULT_REGISTRY if config.tool.enabled else ToolRegistry()
    context = ToolContext(
        session_id="",
        trace_id="",
        sandbox_root=config.tool.sandbox_root,
        max_file_size=config.tool.max_file_size,
    )
    agent = Agent(
        container.resolve(Service.LLM),
        tool_executor=RegistryExecutor(registry, context),
        short_term=container.resolve(Service.SHORT_TERM),
    )
    mid = container.resolve(Service.MID_TERM)
    if mid is not None:
        agent = agent.with_mid_term(mid, config.systemdb.pool_timeout_seconds)
    system = container.resolve(Service.SYSTEM_DB)
    if system is not None:
        agent = agent.with_system_db(system, config.systemdb.pool_timeout_seconds)
    builder = container.resolve(Service.CONTEXT)
    if builder is not None:
        prompt_path = config.prompt.system_prompt_path
        system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else None
        agent = agent.with_context(builder, system_prompt=system_prompt)
    return agent


def _build_app(container: Container) -> Any:
    from agent_mini.interface.http import create_app

    checks: dict[str, Any] = {}
    redis = container.resolve(Service.SHORT_TERM)
    if redis is not None:
        checks["redis"] = lambda: _redis_health(redis)
    mongo = container.resolve(Service.MID_TERM)
    if mongo is not None:
        checks["mongo"] = lambda: _mongo_health(mongo)
    system = container.resolve(Service.SYSTEM_DB)
    if system is not None:
        checks["mysql"] = lambda: _mysql_health(system)
    return create_app(container.resolve(Service.AGENT), checks)


def _build_short_term(config: AppConfig) -> Any:
    if config.redis_url is None:
        return None
    from redis.asyncio import Redis

    from agent_mini.memory.short_term import ShortTermMemory

    client = Redis.from_url(config.redis_url.get_secret_value())
    return ShortTermMemory(client, max_rounds=config.prompt.window_rounds)


def _build_mid_term(config: AppConfig) -> Any:
    if config.mongo_uri is None:
        return None
    from pymongo import AsyncMongoClient

    from agent_mini.memory.mid_term import COLLECTION_NAME, MidTermMemory

    client: Any = AsyncMongoClient(config.mongo_uri.get_secret_value())
    collection: Any = client["agent_mini"][COLLECTION_NAME]
    return MidTermMemory(collection)


def _build_system_db(config: AppConfig) -> Any:
    from agent_mini.systemdb.models import SystemDBConfig as StoreConfig
    from agent_mini.systemdb.repository import SystemDBRepository

    store = StoreConfig(
        dsn=config.systemdb.dsn.get_secret_value(),
        pool_size=config.systemdb.pool_size,
        pool_timeout_seconds=config.systemdb.pool_timeout_seconds,
        auto_create=config.systemdb.auto_create,
    )
    return SystemDBRepository(store)


def _build_context(config: AppConfig) -> Any:
    from agent_mini.context.builder import ContextBuilder
    from agent_mini.context.token_counter import TokenCounter

    return ContextBuilder(
        TokenCounter(),
        DEFAULT_CONTEXT_TOKENS,
        max_rounds=config.prompt.window_rounds,
    )


async def _redis_health(memory: Any) -> bool:
    return bool(await memory._client.ping())


async def _mongo_health(memory: Any) -> bool:
    collection = memory._collection
    return bool(await collection.database.command("ping"))


async def _mysql_health(repository: Any) -> bool:
    from sqlalchemy import text

    async with repository.engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True
