import logging
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _capture_agent_logs(caplog: pytest.LogCaptureFixture) -> Iterator[None]:
    """把 caplog handler 挂到 agent_mini，兼容 propagate=False。"""
    logger = logging.getLogger("agent_mini")
    logger.addHandler(caplog.handler)
    yield
    logger.removeHandler(caplog.handler)
