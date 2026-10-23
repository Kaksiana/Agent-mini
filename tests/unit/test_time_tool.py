"""TC-L1-004/005：time 工具时区与错误。"""

from datetime import UTC, datetime, tzinfo

import pytest

from agent_mini.tools.builtin.time_tool import current_time
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = pytest.mark.unit
FIXED_UTC = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _fixed(zone: tzinfo) -> datetime:
    return FIXED_UTC.astimezone(zone)


def test_default_timezone_is_shanghai() -> None:
    result = current_time(now_provider=_fixed)

    assert result.ok is True
    assert result.content == "2026-01-01T08:00:00+08:00 Asia/Shanghai"


def test_tz_keyword_uses_utc() -> None:
    result = current_time(tz="UTC", now_provider=_fixed)

    assert result.ok is True
    assert result.content == "2026-01-01T00:00:00+00:00 UTC"


def test_naive_provider_is_interpreted_in_zone() -> None:
    result = current_time(
        timezone="Asia/Shanghai",
        now_provider=lambda zone: datetime(2026, 1, 1, 0, 0),
    )

    assert result.content == "2026-01-01T00:00:00+08:00 Asia/Shanghai"


@pytest.mark.parametrize("bad", ["Mars/Base", "", "utc", 123])
def test_invalid_timezone_is_structured(bad: object) -> None:
    result = current_time(tz=bad, now_provider=_fixed)

    assert result.ok is False
    assert result.error_code == "invalid_timezone"


def test_timezone_field_has_priority_over_tz() -> None:
    result = current_time(
        timezone="UTC",
        tz="Asia/Shanghai",
        now_provider=_fixed,
    )

    assert "+00:00" in result.content


def test_registry_exposes_only_timezone() -> None:
    schema = DEFAULT_REGISTRY.get("time").to_json_schema()
    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    assert "timezone" in properties
    assert "tz" not in properties


async def test_registry_timezone_path() -> None:
    result = await DEFAULT_REGISTRY.execute(
        "time",
        {"timezone": "UTC"},
    )

    assert result.ok is True
    assert "+00:00" in result.content


async def test_registry_non_string_timezone_is_invalid_timezone() -> None:
    result = await DEFAULT_REGISTRY.execute("time", {"timezone": 123})

    assert result.ok is False
    assert result.error_code == "invalid_timezone"


def test_schema_description_does_not_expose_tz() -> None:
    schema = DEFAULT_REGISTRY.get("time").to_json_schema()
    serialized = str(schema)

    assert "tz" not in serialized
    assert "别名" not in serialized
