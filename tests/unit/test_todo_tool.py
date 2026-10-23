"""TC-L1-006/TC-L3-013：todo 会话隔离与上下文注入。"""

import json
from typing import cast

import pytest

from agent_mini.tools.builtin.todo import reset_todo_store, todo
from agent_mini.tools.registry import DEFAULT_REGISTRY, ToolContext, ToolResult

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_store() -> None:
    reset_todo_store()


def _items(result: ToolResult) -> list[dict[str, object]]:
    assert result.ok is True
    data = json.loads(result.content)
    return cast(list[dict[str, object]], data["items"])


def test_add_list_complete_same_session() -> None:
    context = ToolContext(session_id="s1", trace_id="t1")

    todo("add", "a", context=context)
    todo("add", "b", context=context)
    first = _items(todo("list", context=context))
    todo("complete", index=1, context=context)
    second = _items(todo("list", context=context))

    assert len(first) == 2
    assert second[0]["id"] == 1
    assert second[0]["status"] == "done"
    assert second[1]["status"] == "open"


def test_sessions_are_isolated() -> None:
    a = ToolContext(session_id="A", trace_id="ta")
    b = ToolContext(session_id="B", trace_id="tb")

    todo("add", "a", context=a)
    todo("add", "b", context=b)

    assert [item["content"] for item in _items(todo("list", context=a))] == ["a"]
    assert [item["content"] for item in _items(todo("list", context=b))] == ["b"]


def test_empty_list_returns_empty_items() -> None:
    result = todo("list", context=ToolContext(session_id="empty", trace_id="t"))

    assert _items(result) == []


def test_missing_context_is_structured() -> None:
    result = todo("list")

    assert result.ok is False
    assert result.error_code == "missing_context"


@pytest.mark.parametrize(
    ("kwargs", "error_code"),
    [
        ({"action": "add", "content": " "}, "empty_content"),
        ({"action": "complete", "index": 0}, "invalid_index"),
        ({"action": "complete", "index": 99}, "todo_not_found"),
        ({"action": "bogus"}, "invalid_action"),
    ],
)
def test_invalid_arguments_are_structured(
    kwargs: dict[str, object],
    error_code: str,
) -> None:
    result = todo(**kwargs, context=ToolContext(session_id="s", trace_id="t"))

    assert result.ok is False
    assert result.error_code == error_code


def test_delete_does_not_renumber() -> None:
    context = ToolContext(session_id="s", trace_id="t")
    todo("add", "a", context=context)
    todo("add", "b", context=context)

    todo("delete", index=1, context=context)

    assert [item["id"] for item in _items(todo("list", context=context))] == [2]


def test_registry_injects_context_and_rejects_forged_session() -> None:
    import asyncio

    async def run() -> None:
        context = ToolContext(session_id="A", trace_id="t")
        added = await DEFAULT_REGISTRY.execute(
            "todo",
            {"action": "add", "content": "a"},
            context=context,
        )
        listed = await DEFAULT_REGISTRY.execute(
            "todo",
            {"action": "list"},
            context=context,
        )
        forged = await DEFAULT_REGISTRY.execute(
            "todo",
            {"action": "list", "session_id": "B"},
            context=context,
        )
        assert added.ok is True
        assert len(json.loads(listed.content)["items"]) == 1
        assert forged.error_code == "invalid_arguments"

    asyncio.run(run())


def test_schema_does_not_expose_session_id() -> None:
    schema = DEFAULT_REGISTRY.get("todo").to_json_schema()
    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    assert "session_id" not in properties
