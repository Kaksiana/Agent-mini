"""TC-L1-021：search 未配置、provider 透传与边界。"""

import json
from collections.abc import Sequence
from typing import cast

import pytest

from agent_mini.tools.builtin.search import (
    SearchProvider,
    SearchResult,
    configure_search_provider,
    reset_search_provider,
    search,
)

pytestmark = pytest.mark.unit


class FakeProvider:
    name = "fake"

    def __init__(self, results: Sequence[SearchResult] | Exception) -> None:
        self.results = results
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, limit: int) -> Sequence[SearchResult]:
        self.calls.append((query, limit))
        if isinstance(self.results, Exception):
            raise self.results
        return self.results


@pytest.fixture(autouse=True)
def _reset_provider() -> None:
    reset_search_provider()


async def test_unconfigured_returns_not_configured_without_fake_results() -> None:
    result = await search("今天天气")

    assert result.ok is False
    assert result.error_code == "not_configured"
    assert "http" not in result.content
    assert "天气" not in result.content


async def test_configured_provider_is_transparent() -> None:
    fake = FakeProvider([SearchResult("天气", "https://example.test/weather", "晴", "fake")])
    configure_search_provider(fake)

    result = await search("今天天气", limit=3)
    body = json.loads(result.content)

    assert result.ok is True
    assert body["provider"] == "fake"
    assert body["truncated"] is False
    assert body["results"][0]["url"] == "https://example.test/weather"
    assert fake.calls == [("今天天气", 3)]


async def test_empty_results_are_success() -> None:
    configure_search_provider(FakeProvider([]))

    result = await search("nothing")

    assert result.ok is True
    assert json.loads(result.content)["results"] == []


@pytest.mark.parametrize(
    ("query", "limit", "error_code"),
    [
        ("", 5, "invalid_query"),
        ("x" * 201, 5, "invalid_query"),
        ("ok", 0, "invalid_limit"),
        ("ok", 11, "invalid_limit"),
    ],
)
async def test_invalid_arguments_are_structured(
    query: str,
    limit: int,
    error_code: str,
) -> None:
    configure_search_provider(FakeProvider([]))
    result = await search(query, limit=limit)

    assert result.ok is False
    assert result.error_code == error_code


async def test_provider_error_is_structured() -> None:
    configure_search_provider(FakeProvider(RuntimeError("boom")))

    result = await search("query")

    assert result.error_code == "provider_error"


async def test_provider_timeout_is_structured() -> None:
    configure_search_provider(FakeProvider(TimeoutError()))

    result = await search("query")

    assert result.error_code == "provider_timeout"


async def test_malformed_provider_result_is_structured() -> None:
    malformed = cast(Sequence[SearchResult], [{"url": "x"}])
    configure_search_provider(FakeProvider(malformed))

    result = await search("query")

    assert result.error_code == "provider_result_invalid"


async def test_malformed_result_fields_are_structured() -> None:
    bad = SearchResult("title", cast(str, 123), "snippet", "fake")
    configure_search_provider(FakeProvider([bad]))

    result = await search("query")

    assert result.error_code == "provider_result_invalid"


async def test_non_string_provider_name_is_structured() -> None:
    class BadNameProvider:
        name = 123

        async def search(self, query: str, limit: int) -> Sequence[SearchResult]:
            return []

    configure_search_provider(cast(SearchProvider, BadNameProvider()))
    result = await search("query")

    assert result.error_code == "provider_result_invalid"


async def test_registry_search_returns_not_configured() -> None:
    from agent_mini.tools.registry import DEFAULT_REGISTRY

    result = await DEFAULT_REGISTRY.execute("search", {"query": "今天天气"})

    assert result.ok is False
    assert result.error_code == "not_configured"


async def test_results_and_snippet_are_truncated() -> None:
    results = [
        SearchResult(
            f"title-{index}",
            f"https://example.test/{index}",
            "x" * 600,
            "fake",
        )
        for index in range(3)
    ]
    configure_search_provider(FakeProvider(results))

    result = await search("query", limit=2)
    body = json.loads(result.content)

    assert body["truncated"] is True
    assert len(body["results"]) == 2
    assert len(body["results"][0]["snippet"]) == 500
