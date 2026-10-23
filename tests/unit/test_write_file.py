"""S11：write_file 原子写、覆盖与沙箱边界。"""

import json
import os
from pathlib import Path
from typing import Any, cast

import pytest

from agent_mini.tools.builtin.read_file import read_file
from agent_mini.tools.builtin.write_file import write_file
from agent_mini.tools.registry import ToolContext
from agent_mini.tools.sandbox import Sandbox

pytestmark = pytest.mark.unit


def _context(root: Path, limit: int | None = None) -> ToolContext:
    return ToolContext("s", "t", sandbox_root=str(root), max_file_size=limit)


def _temps(root: Path) -> list[Path]:
    return list(root.glob(".write-*"))


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    context = _context(tmp_path)
    payload = json.loads(write_file("a.txt", "line1\nline2\n", context=context).content)

    result = read_file("a.txt", context=context)
    body = json.loads(result.content)

    assert payload["path"] == "a.txt"
    assert payload["size"] == 12
    assert payload["overwritten"] is False
    assert body["content"] == "line1\nline2\n"


def test_default_does_not_overwrite(tmp_path: Path) -> None:
    context = _context(tmp_path)
    (tmp_path / "a.txt").write_text("old")

    result = write_file("a.txt", "new", context=context)

    assert result.error_code == "file_exists"
    assert (tmp_path / "a.txt").read_text() == "old"
    assert _temps(tmp_path) == []


def test_explicit_overwrite(tmp_path: Path) -> None:
    context = _context(tmp_path)
    (tmp_path / "a.txt").write_text("old")

    result = write_file("a.txt", "new", overwrite=True, context=context)

    assert result.ok is True
    assert json.loads(result.content)["overwritten"] is True
    assert (tmp_path / "a.txt").read_text() == "new"
    assert _temps(tmp_path) == []


def test_empty_content_is_allowed(tmp_path: Path) -> None:
    context = _context(tmp_path)
    result = write_file("empty.txt", "", context=context)

    assert result.ok is True
    assert (tmp_path / "empty.txt").read_bytes() == b""
    assert read_file("empty.txt", context=context).ok is True


@pytest.mark.parametrize(
    ("path", "error_code"),
    [
        ("../x.txt", "path_escape"),
        ("/etc/x.txt", "absolute_path"),
        (".hidden.txt", "hidden_path"),
        ("missing/a.txt", "parent_not_found"),
    ],
)
def test_path_validation_does_not_write(
    tmp_path: Path,
    path: str,
    error_code: str,
) -> None:
    result = write_file(path, "x", context=_context(tmp_path))

    assert result.error_code == error_code
    assert _temps(tmp_path) == []


def test_size_limit_does_not_write(tmp_path: Path) -> None:
    result = write_file("big.txt", "a" * 2048, context=_context(tmp_path, 1024))

    assert result.error_code == "file_too_large"
    assert not (tmp_path / "big.txt").exists()
    assert _temps(tmp_path) == []


@pytest.mark.parametrize("encoding", ["base64", "hex", ""])
def test_non_text_encoding_is_rejected(tmp_path: Path, encoding: str) -> None:
    result = write_file("a.txt", "x", encoding=encoding, context=_context(tmp_path))

    assert result.error_code == "invalid_encoding"
    assert _temps(tmp_path) == []


def test_symlink_target_escape_is_blocked(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret")
    root = tmp_path / "root"
    root.mkdir()
    link = root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        import subprocess

        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            check=True,
        )

    result = write_file("link/secret.txt", "x", overwrite=True, context=_context(root))

    assert result.error_code == "path_escape"
    assert secret.read_text() == "secret"


@pytest.mark.skipif(os.name != "posix", reason="POSIX dir_fd path only")
def test_posix_parent_symlink_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.txt").write_text("original")
    (root / "link").symlink_to(outside, target_is_directory=True)
    target = root / "link" / "a.txt"
    monkeypatch.setattr(Sandbox, "resolve", lambda self, path: target)

    result = write_file("a.txt", "x", overwrite=True, context=_context(root))

    assert result.error_code == "path_escape"
    assert (outside / "a.txt").read_text() == "original"
    assert list(outside.glob(".write-*")) == []


def test_parent_reparse_after_resolve_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        import subprocess

        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True)
    target = link / "a.txt"
    monkeypatch.setattr(Sandbox, "resolve", lambda self, path: target)

    result = write_file("a.txt", "x", context=_context(root))

    assert result.error_code == "path_escape"
    assert not (outside / "a.txt").exists()


def test_replace_failure_leaves_no_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(source: object, target: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    result = write_file("a.txt", "x", overwrite=True, context=_context(tmp_path))

    assert result.error_code == "file_write_error"
    assert not (tmp_path / "a.txt").exists()
    assert _temps(tmp_path) == []


def test_concurrent_create_is_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tempfile

    original = tempfile.mkstemp

    def create_competitor(*args: Any, **kwargs: Any) -> tuple[int, str]:
        descriptor, path = original(*args, **kwargs)
        (tmp_path / "a.txt").write_text("competitor")
        return descriptor, path

    monkeypatch.setattr(tempfile, "mkstemp", create_competitor)
    result = write_file("a.txt", "mine", context=_context(tmp_path))

    assert result.error_code == "file_exists"
    assert (tmp_path / "a.txt").read_text() == "competitor"
    assert _temps(tmp_path) == []


def test_parent_swap_before_publish_is_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tempfile

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    original = tempfile.mkstemp

    def create_outside(*args: Any, **kwargs: Any) -> tuple[int, str]:
        return original(dir=outside, prefix=".write-", suffix=".tmp")

    monkeypatch.setattr(tempfile, "mkstemp", create_outside)
    result = write_file("a.txt", "x", context=_context(root))

    assert result.error_code == "path_escape"
    assert list(outside.glob(".write-*")) == []
    assert not (outside / "a.txt").exists()


def test_overwrite_non_bool_is_rejected(tmp_path: Path) -> None:
    result = write_file("a.txt", "x", overwrite="yes", context=_context(tmp_path))

    assert result.error_code == "invalid_overwrite"


def test_missing_root_is_structured() -> None:
    result = write_file("a.txt", "x", context=ToolContext("s", "t"))

    assert result.error_code == "missing_sandbox_root"


def test_unknown_codec_is_structured(tmp_path: Path) -> None:
    result = write_file("a.txt", "x", encoding="no-such-codec", context=_context(tmp_path))

    assert result.error_code == "invalid_encoding"


def test_non_string_content_is_structured(tmp_path: Path) -> None:
    result = write_file("a.txt", cast(str, 123), context=_context(tmp_path))

    assert result.error_code == "invalid_content"


def test_unencodable_content_is_structured(tmp_path: Path) -> None:
    result = write_file("a.txt", "é", encoding="ascii", context=_context(tmp_path))

    assert result.error_code == "invalid_encoding"
