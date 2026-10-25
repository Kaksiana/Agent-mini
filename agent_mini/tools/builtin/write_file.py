"""S11 write_file：沙箱内原子写与覆盖保护。"""

import codecs
import ctypes
import json
import logging
import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import uuid4

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
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_FCHMOD = getattr(os, "fchmod", None)


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
    if os.name == "posix":  # pragma: no cover - exercised on POSIX CI
        _posix_publish(target, data, mode, root, overwrite)
        return
    with _locked_parent(target.parent, root):
        descriptor, temporary = tempfile.mkstemp(
            dir=target.parent,
            prefix=".write-",
            suffix=".tmp",
        )
        temp_path = Path(temporary)
        try:
            _publish_temp(descriptor, temp_path, target, data, (mode, overwrite))
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise


def _publish_temp(
    descriptor: int,
    temp_path: Path,
    target: Path,
    data: bytes,
    options: tuple[int | None, bool],
) -> None:
    mode, overwrite = options
    if temp_path.parent.resolve() != target.parent.resolve():
        os.close(descriptor)
        raise SandboxViolation("path_escape", "临时文件目录不一致")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        with suppress(OSError):
            os.close(descriptor)
        raise
    if mode is not None:
        os.chmod(temp_path, mode)
    if overwrite:
        os.replace(temp_path, target)
        return
    try:
        os.link(temp_path, target)
    except FileExistsError as exc:
        raise _TargetExistsError from exc
    temp_path.unlink(missing_ok=True)


def _posix_publish(  # pragma: no cover - POSIX-only
    target: Path,
    data: bytes,
    mode: int | None,
    root: Path,
    overwrite: bool,
) -> None:
    parent_fd = os.open(root, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    opened: list[int] = [parent_fd]
    temp_name = f".write-{uuid4().hex}.tmp"
    publishing = False
    try:
        for part in target.parent.relative_to(root).parts:
            child = os.open(
                part,
                os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            opened.append(child)
            parent_fd = child
        descriptor = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        try:
            _write_fd(descriptor, data)
            if mode is not None and callable(_FCHMOD):
                _FCHMOD(descriptor, mode)
        finally:
            os.close(descriptor)
        publishing = True
        if overwrite:
            os.replace(
                temp_name,
                target.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            return
        try:
            os.link(
                temp_name,
                target.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        except FileExistsError as exc:
            raise _TargetExistsError from exc
        os.unlink(temp_name, dir_fd=parent_fd)
    except _TargetExistsError:
        with suppress(OSError):
            os.unlink(temp_name, dir_fd=parent_fd)
        raise
    except OSError as exc:
        with suppress(OSError):
            os.unlink(temp_name, dir_fd=parent_fd)
        if publishing:
            raise
        raise SandboxViolation("path_escape", "POSIX 发布失败") from exc
    finally:
        for file_descriptor in reversed(opened):
            os.close(file_descriptor)


def _write_fd(descriptor: int, data: bytes) -> None:  # pragma: no cover - POSIX-only
    remaining = memoryview(data)
    while remaining:
        written = os.write(descriptor, remaining)
        remaining = remaining[written:]
    os.fsync(descriptor)


@contextmanager
def _locked_parent(parent: Path, root: Path) -> Generator[None, None, None]:
    """锁 root→parent 目录链；Windows 不共享 DELETE，阻止替换。"""
    if os.name != "nt":
        yield
        return
    handles: list[int] = []
    try:
        chain = [root, *[root / part for part in parent.relative_to(root).parts]]
        for current in chain:
            handle = _open_dir_handle(current)
            handles.append(handle)
            _validate_handle(handle, current)
        yield
    finally:
        for handle in reversed(handles):
            ctypes.windll.kernel32.CloseHandle(handle)


def _open_dir_handle(path: Path) -> int:
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    handle = kernel32.CreateFileW(
        str(path),
        0x80,
        3,
        None,
        3,
        0x02000000 | 0x00200000,
        None,
    )
    if not handle or handle == ctypes.c_void_p(-1).value:
        raise SandboxViolation("path_escape", "无法锁定父目录")
    return int(handle)


def _validate_handle(handle: int, expected: Path) -> None:
    kernel32 = ctypes.windll.kernel32
    kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_uint32
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    buffer = ctypes.create_unicode_buffer(32_768)
    length = kernel32.GetFinalPathNameByHandleW(handle, buffer, 32_768, 0)
    if length == 0:
        raise SandboxViolation("path_escape", "无法校验父目录")
    final = buffer.value.removeprefix("\\\\?\\")
    if os.path.normcase(final) != os.path.normcase(str(expected)):
        raise SandboxViolation("path_escape", "父目录路径不一致")
    info = _FileAttributeTagInfo()
    kernel32.GetFileInformationByHandleEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    if not kernel32.GetFileInformationByHandleEx(
        handle,
        9,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise SandboxViolation("path_escape", "无法读取目录属性")
    if info.attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        raise SandboxViolation("path_escape", "父目录包含重解析点")


class _FileAttributeTagInfo(ctypes.Structure):
    _fields_ = [("attributes", ctypes.c_uint32), ("tag", ctypes.c_uint32)]
