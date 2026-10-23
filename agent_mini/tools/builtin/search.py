"""S12 search：Provider 协议与显式未配置错误。"""

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from agent_mini.tools.registry import ToolResult, tool

MAX_QUERY_CHARS = 200
MAX_RESULTS = 10
DEFAULT_RESULTS = 5
MAX_SNIPPET_CHARS = 500
SEARCH_TIMEOUT_SECONDS = 5.0
ERROR_NOT_CONFIGURED = "not_configured"
ERROR_INVALID_QUERY = "invalid_query"
ERROR_INVALID_LIMIT = "invalid_limit"
ERROR_PROVIDER = "provider_error"
ERROR_TIMEOUT = "provider_timeout"
ERROR_RESULT_INVALID = "provider_result_invalid"


@dataclass(frozen=True)
class SearchResult:
    """一条搜索结果的公开结构。"""

    title: str
    url: str
    snippet: str
    source: str


class SearchProvider(Protocol):
    """搜索 provider 的异步协议。"""

    @property
    def name(self) -> str:
        """provider 名称。"""
        ...

    async def search(self, query: str, limit: int) -> Sequence[SearchResult]:
        """执行搜索，返回不超过/超过 limit 的结果。"""
        ...


class NullProvider:
    """未配置占位；绝不返回伪造结果。"""

    @property
    def name(self) -> str:
        """固定名称。"""
        return "null"

    async def search(self, query: str, limit: int) -> Sequence[SearchResult]:
        """返回空序列；handler 会在调用前拒绝。"""
        return []


class SearchArgs(BaseModel):
    """search 参数。"""

    query: str
    limit: int = Field(default=DEFAULT_RESULTS, strict=True)


_PROVIDER: SearchProvider = NullProvider()


def configure_search_provider(provider: SearchProvider) -> None:
    """注入 provider；S21 DI 接管前的测试/装配入口。"""
    global _PROVIDER
    _PROVIDER = provider


def reset_search_provider() -> None:
    """恢复 NullProvider。"""
    global _PROVIDER
    _PROVIDER = NullProvider()


@tool(
    "search",
    "通过注入的 SearchProvider 搜索；未配置时显式报错。",
    SearchArgs,
)
async def search(query: str, limit: int = DEFAULT_RESULTS) -> ToolResult:
    """执行搜索并返回 JSON；未配置绝不伪造结果。"""
    if isinstance(_PROVIDER, NullProvider):
        return ToolResult(False, "搜索 provider 未配置", ERROR_NOT_CONFIGURED)
    invalid = _validate_arguments(query, limit)
    if invalid is not None:
        return invalid
    try:
        raw = await asyncio.wait_for(_PROVIDER.search(query, limit), SEARCH_TIMEOUT_SECONDS)
    except TimeoutError:
        return ToolResult(False, "搜索超时", ERROR_TIMEOUT)
    except Exception:
        return ToolResult(False, "搜索 provider 失败", ERROR_PROVIDER)
    name = _provider_name()
    if isinstance(name, ToolResult):
        return name
    return _render(raw, limit, name)


def _provider_name() -> str | ToolResult:
    try:
        name = getattr(_PROVIDER, "name", None)
    except Exception:
        return ToolResult(False, "provider 名称读取失败", ERROR_RESULT_INVALID)
    if not isinstance(name, str):
        return ToolResult(False, "provider 名称不合法", ERROR_RESULT_INVALID)
    return name


def _validate_arguments(query: str, limit: int) -> ToolResult | None:
    if not query.strip() or len(query) > MAX_QUERY_CHARS:
        return ToolResult(False, "查询不能为空且不超过 200 字符", ERROR_INVALID_QUERY)
    if limit < 1 or limit > MAX_RESULTS:
        return ToolResult(False, "结果条数必须在 1..10", ERROR_INVALID_LIMIT)
    return None


def _render(raw: object, limit: int, provider_name: str) -> ToolResult:
    if not isinstance(raw, Sequence):
        return ToolResult(False, "provider 返回结构不合法", ERROR_RESULT_INVALID)
    results = list(raw)
    if any(not _valid_result(item) for item in results):
        return ToolResult(False, "provider 返回结构不合法", ERROR_RESULT_INVALID)
    truncated = len(results) > limit
    selected = results[:limit]
    payload = []
    for item in selected:
        snippet = item.snippet[:MAX_SNIPPET_CHARS]
        if len(item.snippet) > MAX_SNIPPET_CHARS:
            truncated = True
        payload.append(
            {
                "title": item.title,
                "url": item.url,
                "snippet": snippet,
                "source": item.source,
            }
        )
    body = {
        "provider": provider_name,
        "truncated": truncated,
        "results": payload,
    }
    return ToolResult(True, json.dumps(body, ensure_ascii=False))


def _valid_result(item: object) -> bool:
    return isinstance(item, SearchResult) and all(
        isinstance(value, str) for value in (item.title, item.url, item.snippet, item.source)
    )
