"""S11 write_file：沙箱内原子写与覆盖保护。"""

import codecs
import json
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from agent_mini.tools.registry import ToolContext, ToolResult, tool
from agent_mini.tools.sandbox import MAX_FILE_SIZE, Sandbox, SandboxViolation

ERROR_MISSING_ROOT = "missing_sandbox_root"
ERROR_INVALID_ENCODING = "invalid_encoding"
ERROR_FILE_EXISTS = "file_exists"
ERROR_PARENT = "parent_not_found"
ERROR_TOO_LARGE = "file_too_large"
ERROR_WRITE = "file_write_error"
ERROR_INVALID_OVERWRITE = "invalid_overwrite"
ERROR_INVALID_CONTENT = "invalid_content"
DEFAULT_ENCODING = "utf-8"


class WriteFileArgs(BaseModel):
    """write_file 参数；沙箱根不在模型中。"""

    path: str
    content: str
    overwrite: bool = Field(default=False, strict=True)
    encoding: str | None = None


@tool(
    "write_file",
    "在沙箱内原子写入文本文件，默认不覆盖已有文件。",
    WriteFileArgs,
)
def write_file(
    path: str,
    content: str,
    overwrite: bool = False,
    encoding: str | None = None,
    context: ToolContext | None = None,
) -> ToolResult:
    """写入文件并返回路径/字节数/是否覆盖；失败不抛异常。"""
    if context is None or context.sandbox_root is None:
        return ToolResult(False, "缺少沙箱根目录", ERROR_MISSING_ROOT)
    selected, error = _validate_options(overwrite, encoding)
    if error is not None:
        return ToolResult(False, error[1], error[0])
    limit = context.max_file_size if context.max_file_size is not None else MAX_FILE_SIZE
    sandbox = Sandbox(context.sandbox_root, max_file_size=limit)
    try:
        target = sandbox.resolve(path)
    except SandboxViolation as exc:
        return ToolResult(False, str(exc), exc.error_code)
    data, exists, error = _prepare(target, content, selected, overwrite, limit)
    if error is not None:
        return ToolResult(False, error[1], error[0])
    try:
        _atomic_write(target, data, target.stat().st_mode & 0o777 if exists else None)
    except OSError:
        return ToolResult(False, "文件写入失败", ERROR_WRITE)
    relative = target.relative_to(sandbox.root).as_posix()
    payload = {"path": relative, "size": len(data), "overwritten": exists}
    return ToolResult(True, json.dumps(payload, ensure_ascii=False))


def _validate_options(
    overwrite: bool,
    encoding: str | None,
) -> tuple[str, tuple[str, str] | None]:
    if not isinstance(overwrite, bool):
        return DEFAULT_ENCODING, (ERROR_INVALID_OVERWRITE, "overwrite 必须是布尔值")
    selected = DEFAULT_ENCODING if encoding is None else encoding
    if not selected:
        return selected, (ERROR_INVALID_ENCODING, "编码不能为空")
    try:
        info = codecs.lookup(selected)
    except LookupError:
        return selected, (ERROR_INVALID_ENCODING, f"不支持的编码: {selected}")
    if not getattr(info, "_is_text_encoding", False):
        return selected, (ERROR_INVALID_ENCODING, f"不是文本编码: {selected}")
    return selected, None


def _prepare(
    target: Path,
    content: str,
    encoding: str,
    overwrite: bool,
    limit: int,
) -> tuple[bytes, bool, tuple[str, str] | None]:
    if not target.parent.is_dir():
        return b"", False, (ERROR_PARENT, "父目录不存在")
    exists = target.exists()
    if exists and not overwrite:
        return b"", True, (ERROR_FILE_EXISTS, "目标文件已存在")
    if not isinstance(content, str):
        return b"", exists, (ERROR_INVALID_CONTENT, "content 必须是字符串")
    try:
        data = content.encode(encoding)
    except UnicodeEncodeError:
        return b"", exists, (ERROR_INVALID_ENCODING, "内容编码失败")
    if len(data) > limit:
        return b"", exists, (ERROR_TOO_LARGE, "内容超过大小限制")
    return data, exists, None


def _atomic_write(target: Path, data: bytes, mode: int | None) -> None:
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent,
        prefix=".write-",
        suffix=".tmp",
    )
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp_path, mode)
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
