"""S10 read_file：沙箱内只读文本文件。"""

import codecs
import json
from pathlib import Path

from pydantic import BaseModel

from agent_mini.tools.registry import ToolContext, ToolResult, tool
from agent_mini.tools.sandbox import MAX_FILE_SIZE, Sandbox, SandboxViolation

ERROR_MISSING_ROOT = "missing_sandbox_root"
ERROR_NOT_FOUND = "file_not_found"
ERROR_TOO_LARGE = "file_too_large"
ERROR_BINARY = "binary_file"
ERROR_DECODE = "decode_error"
ERROR_ENCODING = "invalid_encoding"
ERROR_READ = "file_read_error"
DEFAULT_ENCODING = "utf-8"


class ReadFileArgs(BaseModel):
    """read_file 参数；沙箱根不在模型中。"""

    path: str
    encoding: str | None = None


@tool(
    "read_file",
    "读取沙箱内文本文件，返回内容、大小与编码。",
    ReadFileArgs,
)
def read_file(
    path: str,
    encoding: str | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    """读取文件并返回 JSON 元信息；所有失败结构化。"""
    if context is None or context.sandbox_root is None:
        return ToolResult(False, "缺少沙箱根目录", ERROR_MISSING_ROOT)
    selected = DEFAULT_ENCODING if encoding is None else encoding
    if not selected:
        return ToolResult(False, "编码不能为空", ERROR_ENCODING)
    try:
        info = codecs.lookup(selected)
    except LookupError:
        return ToolResult(False, f"不支持的编码: {selected}", ERROR_ENCODING)
    if not getattr(info, "_is_text_encoding", False):
        return ToolResult(False, f"不是文本编码: {selected}", ERROR_ENCODING)
    limit = context.max_file_size if context.max_file_size is not None else MAX_FILE_SIZE
    sandbox = Sandbox(context.sandbox_root, max_file_size=limit)
    try:
        target = sandbox.resolve(path)
    except SandboxViolation as exc:
        return ToolResult(False, str(exc), exc.error_code)
    return _read_target(target, selected, limit)


def _read_target(target: Path, encoding: str, limit: int) -> ToolResult:
    data, error = _load_bounded(target, limit)
    if error is not None:
        return ToolResult(False, _ERROR_MESSAGES[error], error)
    if b"\x00" in data:
        return ToolResult(False, "不允许读取二进制文件", ERROR_BINARY)
    return _decode(data, encoding)


def _load_bounded(target: Path, limit: int) -> tuple[bytes, str | None]:
    size, error = _stat_size(target)
    if error is not None:
        return b"", error
    if size > limit:
        return b"", ERROR_TOO_LARGE
    try:
        with target.open("rb") as handle:
            data = handle.read(limit + 1)
    except FileNotFoundError:
        return b"", ERROR_NOT_FOUND
    except OSError:
        return b"", ERROR_READ
    if len(data) > limit:
        return b"", ERROR_TOO_LARGE
    return data, None


def _stat_size(target: Path) -> tuple[int, str | None]:
    try:
        return target.stat().st_size, None
    except FileNotFoundError:
        return 0, ERROR_NOT_FOUND
    except OSError:
        return 0, ERROR_READ


def _decode(data: bytes, encoding: str) -> ToolResult:
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        return ToolResult(False, "文件解码失败", ERROR_DECODE)
    payload = {"content": text, "size": len(data), "encoding": encoding}
    return ToolResult(True, json.dumps(payload, ensure_ascii=False))


_ERROR_MESSAGES = {
    ERROR_NOT_FOUND: "文件不存在",
    ERROR_READ: "文件读取失败",
    ERROR_TOO_LARGE: "文件超过大小限制",
}
