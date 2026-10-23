"""S10 文件沙箱：root + realpath 四步校验。"""

from pathlib import Path, PurePosixPath, PureWindowsPath

MAX_FILE_SIZE = 1024 * 1024
MAX_PATH_CHARS = 240
ALLOWED_EXTENSIONS = frozenset({".txt", ".md", ".json", ".csv", ".log", ".py", ".yaml", ".yml"})
ERROR_ABSOLUTE = "absolute_path"
ERROR_ESCAPE = "path_escape"
ERROR_INVALID = "invalid_path"
ERROR_HIDDEN = "hidden_path"
ERROR_EXTENSION = "extension_not_allowed"
ERROR_TOO_LONG = "path_too_long"


class SandboxViolationError(Exception):
    """沙箱校验失败，携带稳定 error_code。"""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class Sandbox:
    """把相对路径限制在 root 内；不承诺抵御 resolve/open 间竞态。"""

    def __init__(
        self,
        root: str | Path,
        max_file_size: int = MAX_FILE_SIZE,
        allowed_extensions: frozenset[str] = ALLOWED_EXTENSIONS,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions

    def resolve(self, rel_path: str) -> Path:
        """执行四步校验并返回真实路径；失败抛 SandboxViolation。"""
        if not rel_path or rel_path == ".":
            raise SandboxViolation(ERROR_INVALID, "路径不能为空")
        if PurePosixPath(rel_path).is_absolute() or PureWindowsPath(rel_path).is_absolute():
            raise SandboxViolation(ERROR_ABSOLUTE, "不允许绝对路径")
        if "\x00" in rel_path or ":" in rel_path:
            raise SandboxViolation(ERROR_INVALID, "路径包含非法字符")
        if len(rel_path) > MAX_PATH_CHARS:
            raise SandboxViolation(ERROR_TOO_LONG, "路径过长")
        parts = PurePosixPath(rel_path).parts
        if any(part.startswith(".") and part not in {".", ".."} for part in parts):
            raise SandboxViolation(ERROR_HIDDEN, "不允许隐藏路径")
        candidate = (self.root / rel_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise SandboxViolation(ERROR_ESCAPE, "路径越界")
        if candidate.suffix not in self.allowed_extensions:
            raise SandboxViolation(ERROR_EXTENSION, "扩展名不在白名单")
        return candidate


SandboxViolation = SandboxViolationError
