"""S11 write_file：沙箱内原子写与覆盖保护。"""

import codecs
import json
import logging
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
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
LOGGER = logging.getLogger("agent_mini.tools.write_file")


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
    return _commit(target, data, exists, sandbox.root, overwrite)


def _commit(
    target: Path,
    data: bytes,
    exists: bool,
    root: Path,
    overwrite: bool,
) -> ToolResult:
    try:
        _atomic_write(
            target,
            data,
            target.stat().st_mode & 0o777 if exists else None,
            root,
            overwrite,
        )
    except _TargetExistsError:
        return ToolResult(False, "目标文件已存在", ERROR_FILE_EXISTS)
    except SandboxViolation as exc:
        return ToolResult(False, str(exc), exc.error_code)
    except OSError:
        return ToolResult(False, "文件写入失败", ERROR_WRITE)
    relative = target.relative_to(root).as_posix()
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


class _TargetExistsError(Exception):
    """原子发布发现目标已存在。"""


def _atomic_write(
    target: Path,
    data: bytes,
    mode: int | None,
    root: Path,
    overwrite: bool,
) -> None:
    _assert_no_reparse(target.parent, root)
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent,
        prefix=".write-",
        suffix=".tmp",
    )
    temp_path = Path(temporary)
    committed = False
    try:
        _assert_inside(target.parent, root)
        _assert_inside(temp_path, root)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temp_path, mode)
        _assert_inside(target.parent, root)
        _assert_no_reparse(target.parent, root)
        if overwrite:
            os.replace(temp_path, target)
            committed = True
        else:
            try:
                os.link(temp_path, target)
            except FileExistsError as exc:
                raise _TargetExistsError from exc
            committed = True
            temp_path.unlink(missing_ok=True)
        _assert_inside(target, root)
    except Exception:
        if committed:
            LOGGER.warning(
                "write_file.committed_outside",
                extra={"event": "write_file.committed_outside"},
            )
        if descriptor >= 0:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)
        raise


def _assert_inside(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise SandboxViolation("path_escape", "路径在写入期间越界")


def _assert_no_reparse(path: Path, root: Path) -> None:
    current = path
    while current != root and current != current.parent:
        try:
            attributes = current.lstat().st_file_attributes
        except AttributeError:
            attributes = 0
        except OSError as exc:
            raise SandboxViolation("path_escape", "父目录不可信") from exc
        if current.is_symlink() or attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise SandboxViolation("path_escape", "父目录包含重解析点")
        current = current.parent
