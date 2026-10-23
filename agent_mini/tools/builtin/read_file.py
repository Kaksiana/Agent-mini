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
    selected = encoding or DEFAULT_ENCODING
    try:
        codecs.lookup(selected)
    except LookupError:
        return ToolResult(False, f"不支持的编码: {selected}", ERROR_ENCODING)
    limit = context.max_file_size if context.max_file_size is not None else MAX_FILE_SIZE
    sandbox = Sandbox(context.sandbox_root, max_file_size=limit)
    try:
        target = sandbox.resolve(path)
    except SandboxViolation as exc:
        return ToolResult(False, str(exc), exc.error_code)
    return _read_target(target, selected, limit)


def _read_target(target: Path, encoding: str, limit: int) -> ToolResult:
    try:
        stat = target.stat()
    except OSError:
        return ToolResult(False, "文件不存在", ERROR_NOT_FOUND)
    if stat.st_size > limit:
        return ToolResult(False, "文件超过大小限制", ERROR_TOO_LARGE)
    try:
        data = target.read_bytes()
    except OSError:
        return ToolResult(False, "文件读取失败", ERROR_NOT_FOUND)
    if b"\x00" in data:
        return ToolResult(False, "不允许读取二进制文件", ERROR_BINARY)
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        return ToolResult(False, "文件解码失败", ERROR_DECODE)
    payload = {"content": text, "size": len(data), "encoding": encoding}
    return ToolResult(True, json.dumps(payload, ensure_ascii=False))
