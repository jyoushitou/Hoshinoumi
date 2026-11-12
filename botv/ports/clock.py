# ===================== 时钟端口（DI 用） =====================
# 目的：把时间来源做成可注入的端口，测试时能冻结时间。
#
# 实现统一放在 botv/core/clock.py（不依赖任何业务模块）；
# 这里只保留接口和默认实现，避免两套时间逻辑。

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from ..core import clock as _clock

CST = timezone(timedelta(hours=8))   # 东八区


@runtime_checkable
class Clock(Protocol):
    """时间端口"""

    def now(self) -> datetime: ...


class SystemClock:
    """默认实现：东八区系统时钟（委托 core.clock）"""

    def __init__(self, tz=CST):
        self._tz = tz

    def now(self) -> datetime:
        return _clock.now(self._tz)


def default_clock() -> Clock:
    """默认时钟（东八区）"""
    return SystemClock(CST)
