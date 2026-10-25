"""S21 可执行 HTTP 启动入口：配置错误单行退出。"""

from __future__ import annotations

import sys
from collections.abc import Callable

import uvicorn
from fastapi import FastAPI

from agent_mini.interface.http import create_app_from_env
from agent_mini.observability.errors import ConfigError

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main(
    factory: Callable[[], FastAPI] = create_app_from_env,
) -> None:
    """构造应用并以 uvicorn 启动；ConfigError 不打印堆栈。"""
    try:
        app = factory()
    except ConfigError as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT)
