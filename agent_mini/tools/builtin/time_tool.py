"""S08 time：按时区返回当前时间。"""

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel

from agent_mini.tools.registry import ToolResult, tool

DEFAULT_TIMEZONE = "Asia/Shanghai"
ERROR_INVALID_TIMEZONE = "invalid_timezone"
NowProvider = Callable[[ZoneInfo], datetime]


class TimeArgs(BaseModel):
    """time 的唯一模型参数；tz 仅为 handler 兼容别名。"""

    timezone: str | None = None


@tool(
    "time",
    "返回指定 IANA 时区的当前时间；默认 Asia/Shanghai。",
    TimeArgs,
)
def current_time(
    timezone: str | None = None,
    tz: str | None = None,
    now_provider: NowProvider | None = None,
) -> ToolResult:
    """解析时区并返回 ISO8601 与时区名；失败不抛异常。"""
    chosen = timezone if timezone is not None else tz
    name = DEFAULT_TIMEZONE if chosen is None else chosen
    if not isinstance(name, str) or not name.strip():
        return ToolResult(False, "时区必须是非空 IANA 名称", ERROR_INVALID_TIMEZONE)
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ToolResult(False, f"无效时区: {name}", ERROR_INVALID_TIMEZONE)
    if name != "UTC" and name.lower() == "utc":
        return ToolResult(False, f"无效时区: {name}", ERROR_INVALID_TIMEZONE)
    now = now_provider(zone) if now_provider is not None else datetime.now(zone)
    now = now.replace(tzinfo=zone) if now.tzinfo is None else now.astimezone(zone)
    return ToolResult(True, f"{now.isoformat()} {zone.key}")
