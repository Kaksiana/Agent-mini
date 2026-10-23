"""TC-L1-010/011/012/TC-L5-003：沙箱与 read_file。"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from agent_mini.tools.builtin.read_file import read_file
from agent_mini.tools.registry import DEFAULT_REGISTRY, ToolContext
from agent_mini.tools.sandbox import Sandbox, SandboxViolation

pytestmark = pytest.mark.unit


def _context(root: Path, limit: int | None = None) -> ToolContext:
    return ToolContext("s", "t", sandbox_root=str(root), max_file_size=limit)


def _write(root: Path, name: str, data: bytes) -> Path:
    path = root / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("rel_path", "error_code"),
    [
        ("../../etc/passwd", "path_escape"),
        ("a/../../../x.txt", "path_escape"),
        ("/etc/passwd", "absolute_path"),
        ("C:\\Windows\\win.ini", "absolute_path"),
        ("", "invalid_path"),
        (".", "invalid_path"),
        (".secret.txt", "hidden_path"),
        ("file.txt:stream", "invalid_path"),
        ("file.TXT", "extension_not_allowed"),
        ("a" * 241 + ".txt", "path_too_long"),
    ],
)
def test_sandbox_blocks_unsafe_paths(
    tmp_path: Path,
    rel_path: str,
    error_code: str,
) -> None:
    sandbox = Sandbox(tmp_path)

    with pytest.raises(SandboxViolation) as exc:
        sandbox.resolve(rel_path)

    assert exc.value.error_code == error_code


def test_sandbox_blocks_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    link = root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("symlink unavailable")
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            check=True,
            capture_output=True,
        )

    with pytest.raises(SandboxViolation) as exc:
        Sandbox(root).resolve("link/secret.txt")

    assert exc.value.error_code == "path_escape"


def test_read_file_empty_file_is_ok(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_bytes(b"")

    result = read_file("empty.txt", context=_context(tmp_path))
    payload = json.loads(result.content)

    assert result.ok is True
    assert payload["content"] == ""
    assert payload["size"] == 0


def test_read_file_returns_metadata(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"line1\nline2\n")

    result = read_file("a.txt", context=_context(tmp_path))
    payload = json.loads(result.content)

    assert payload == {"content": "line1\nline2\n", "size": 12, "encoding": "utf-8"}


def test_read_file_too_large(tmp_path: Path) -> None:
    _write(tmp_path, "big.txt", b"a" * 2048)

    result = read_file("big.txt", context=_context(tmp_path, 1024))

    assert result.error_code == "file_too_large"


def test_read_file_binary(tmp_path: Path) -> None:
    _write(tmp_path, "bin.txt", b"a\x00b")

    result = read_file("bin.txt", context=_context(tmp_path))

    assert result.error_code == "binary_file"


def test_read_file_decode_error(tmp_path: Path) -> None:
    _write(tmp_path, "bad.txt", b"\xff\xfe")

    result = read_file("bad.txt", context=_context(tmp_path))

    assert result.error_code == "decode_error"


def test_read_file_invalid_encoding(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")

    result = read_file("a.txt", encoding="no-such-codec", context=_context(tmp_path))

    assert result.error_code == "invalid_encoding"


def test_read_file_missing_root() -> None:
    result = read_file("a.txt", context=ToolContext("s", "t"))

    assert result.error_code == "missing_sandbox_root"


def test_read_file_missing_file(tmp_path: Path) -> None:
    result = read_file("missing.txt", context=_context(tmp_path))

    assert result.error_code == "file_not_found"


def test_read_file_read_error_is_structured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x")

    def boom(self: Path) -> bytes:
        raise OSError

    monkeypatch.setattr(Path, "read_bytes", boom)
    result = read_file("a.txt", context=_context(tmp_path))

    assert result.error_code == "file_not_found"


def test_read_file_path_escape(tmp_path: Path) -> None:
    result = read_file("../x.txt", context=_context(tmp_path))

    assert result.error_code == "path_escape"


def test_read_file_schema_has_no_root_or_session() -> None:
    schema = DEFAULT_REGISTRY.get("read_file").to_json_schema()
    text = str(schema)

    assert "sandbox_root" not in text
    assert "session_id" not in text
