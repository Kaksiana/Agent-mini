"""S09 todo：会话级待办工具。"""

import json
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from agent_mini.tools.registry import ToolContext, ToolResult, tool

ERROR_MISSING_CONTEXT = "missing_context"
ERROR_INVALID_ACTION = "invalid_action"
ERROR_INVALID_INDEX = "invalid_index"
ERROR_NOT_FOUND = "todo_not_found"
ERROR_EMPTY_CONTENT = "empty_content"


class TodoArgs(BaseModel):
    """todo 的模型参数。"""

    action: str
    content: str | None = None
    index: int | None = Field(default=None, strict=True)


@dataclass(frozen=True)
class TodoItem:
    """一条待办；id 稳定且不随删除重排。"""

    id: int
    content: str
    status: Literal["open", "done"] = "open"


class TodoStore(Protocol):
    """S13 可替换为 Memory KV 的最小存储协议。"""

    def add(self, session_id: str, content: str) -> list[TodoItem]:
        """新增并返回当前列表。"""
        ...

    def list_items(self, session_id: str) -> list[TodoItem]:
        """返回会话列表。"""
        ...

    def complete(self, session_id: str, item_id: int) -> list[TodoItem] | None:
        """完成指定 id；不存在返回 None。"""
        ...

    def delete(self, session_id: str, item_id: int) -> list[TodoItem] | None:
        """删除指定 id；不存在返回 None。"""
        ...

    def clear(self) -> None:
        """清空全部会话，供测试隔离。"""
        ...


class MemoryTodoStore:
    """进程内存储；重启丢失、非线程安全，S13 替换。"""

    def __init__(self) -> None:
        self._items: dict[str, list[TodoItem]] = {}
        self._next_id: dict[str, int] = {}

    def add(self, session_id: str, content: str) -> list[TodoItem]:
        """新增并返回当前列表。"""
        item_id = self._next_id.get(session_id, 1)
        self._next_id[session_id] = item_id + 1
        self._items.setdefault(session_id, []).append(TodoItem(item_id, content))
        return self.list_items(session_id)

    def list_items(self, session_id: str) -> list[TodoItem]:
        """返回会话列表快照。"""
        return [replace(item) for item in self._items.get(session_id, [])]

    def complete(self, session_id: str, item_id: int) -> list[TodoItem] | None:
        """完成指定 id；不存在返回 None。"""
        items = self._items.get(session_id, [])
        for index, item in enumerate(items):
            if item.id == item_id:
                items[index] = replace(item, status="done")
                return self.list_items(session_id)
        return None

    def delete(self, session_id: str, item_id: int) -> list[TodoItem] | None:
        """删除指定 id；不存在返回 None。"""
        items = self._items.get(session_id, [])
        for index, item in enumerate(items):
            if item.id == item_id:
                del items[index]
                return self.list_items(session_id)
        return None

    def clear(self) -> None:
        """清空全部会话。"""
        self._items.clear()
        self._next_id.clear()


_STORE: TodoStore = MemoryTodoStore()


def configure_todo_store(store: TodoStore) -> None:
    """替换存储实现，供 S13/测试注入。"""
    global _STORE
    _STORE = store


def reset_todo_store() -> None:
    """清空进程内存储，供测试隔离。"""
    _STORE.clear()


@tool(
    "todo",
    "会话级待办：add/list/complete/delete，序号从 1 开始。",
    TodoArgs,
)
def todo(
    action: str,
    content: str | None = None,
    index: int | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    """执行会话级待办操作；session_id 只来自 ToolContext。"""
    if context is None:
        return ToolResult(False, "缺少可信会话上下文", ERROR_MISSING_CONTEXT)
    if action == "add":
        return _add(context, content)
    if action == "list":
        return _render(_STORE.list_items(context.session_id))
    if action in {"complete", "delete"}:
        return _change(context, action, index)
    return ToolResult(False, "不支持的待办操作", ERROR_INVALID_ACTION)


def _add(context: ToolContext, content: str | None) -> ToolResult:
    if content is None or not content.strip():
        return ToolResult(False, "待办内容不能为空", ERROR_EMPTY_CONTENT)
    return _render(_STORE.add(context.session_id, content))


def _change(
    context: ToolContext,
    action: str,
    index: int | None,
) -> ToolResult:
    if index is None or index <= 0:
        return ToolResult(False, "待办序号必须从 1 开始", ERROR_INVALID_INDEX)
    result = (
        _STORE.complete(context.session_id, index)
        if action == "complete"
        else _STORE.delete(context.session_id, index)
    )
    if result is None:
        return ToolResult(False, "待办不存在", ERROR_NOT_FOUND)
    return _render(result)


def _render(items: list[TodoItem]) -> ToolResult:
    payload = {
        "items": [{"id": item.id, "content": item.content, "status": item.status} for item in items]
    }
    return ToolResult(True, json.dumps(payload, ensure_ascii=False))
