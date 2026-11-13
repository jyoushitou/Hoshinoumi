# ===================== 统一时钟（东八区） =====================
# 服务器 TZ 可能是 UTC，但「她」活在东八区：
# 日志时间戳、cron 下次触发、深夜判断都必须按北京时间。
#
# 两种时间，别混用：
#   clock.now()    → 带时区的 CST（打印、跨时区计算用）
#   clock.naive()  → 不带时区的 CST 墙钟（和 "2026-11-11 22:30" 这类字符串做算术用）

import time
from datetime import date, datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))   # 东八区（北京时间）
UTC = timezone.utc


def now(tz=None):
    """当前时间（默认按配置的时区；测试可冻结）"""
    tz = tz or _tzinfo()
    fake = _FAKE["value"]
    if fake is not None:
        return to_cst(fake).astimezone(tz) if fake.tzinfo else fake.replace(tzinfo=tz)
    return datetime.now(tz) + _offset_delta()


def naive():
    """当前时区的墙钟值（naive，用于和解析出的字符串时间做算术）"""
    return now().replace(tzinfo=None)


def ts():
    """当前时间戳（秒，与时区无关）"""
    return time.time()


def today():
    """当前北京日期"""
    return naive().date()


def to_naive(dt):
    """带时区 → 北京墙钟（naive）；本来就是 naive 则原样返回"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(CST).replace(tzinfo=None)


def to_cst(dt):
    """naive → 补上东八区；已有时区则转换到 CST"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=CST)
    return dt.astimezone(CST)


def fmt_hms(dt=None):
    return (dt or now()).strftime("%H:%M:%S")


def fmt_ymd(dt=None):
    return (dt or now()).strftime("%Y-%m-%d")


def fmt_full(dt=None):
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def parse(text, fmt="%Y-%m-%d %H:%M:%S"):
    """解析成 naive 北京时间（失败返回 None）"""
    try:
        return datetime.strptime(str(text), fmt)
    except Exception:
        return None


def ensure_tz():
    """把进程时区锁到东八区（run.py 启动时调一次）

    有的容器 TZ 是 UTC，`datetime.now()` 直接给 UTC 时间。
    这里设环境变量 + tzset，保证所有 naive 调用也走北京时间。
    """
    import os

    changed = False
    if os.environ.get("TZ") != "Asia/Shanghai":
        os.environ["TZ"] = "Asia/Shanghai"
        changed = True
    try:
        time.tzset()          # Linux/macOS 生效；Windows 没有这个函数
    except Exception:
        pass
    return changed

# ===================== 自定义时钟（U8） =====================
# 默认东八区；可通过 config.local.json 或环境变量改：
#   {"clock": {"timezone": "Asia/Tokyo", "offset_minutes": 0}}
#   NAO_TZ=Asia/Tokyo
#   NAO_CLOCK_OFFSET=+60      # 整体快 60 分钟（调试/测试）

_FAKE = {"value": None}          # 测试冻结用


def _cfg():
    try:
        from . import settings

        return settings.load().get("clock", {}) or {}
    except Exception:
        return {}


def tz_name():
    """时区名字：配置 > 环境变量 > 默认 Asia/Shanghai"""
    import os

    return (os.getenv("NAO_TZ")
            or _cfg().get("timezone")
            or "Asia/Shanghai")


def offset_minutes():
    """整体偏移（分钟）：配置 > 环境变量 > 0"""
    import os

    raw = os.getenv("NAO_CLOCK_OFFSET") or _cfg().get("offset_minutes") or 0
    try:
        return int(raw)
    except Exception:
        return 0


def _tzinfo():
    """把时区名换成 tzinfo；认不出就回东八区"""
    name = tz_name()
    if name in ("Asia/Shanghai", "CST", "UTC+8", "Etc/GMT-8"):
        return CST
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return CST


def _offset_delta():
    from datetime import timedelta as _td

    return _td(minutes=offset_minutes())


def tz_label():
    """给人看的一行：Asia/Shanghai (UTC+8)"""
    try:
        delta = _tzinfo().utcoffset(datetime.now()) or _offset_delta()
        off = int(delta.total_seconds() // 3600)
    except Exception:
        off = 8
    sign = f"+{off}" if off >= 0 else str(off)
    extra = f"，偏移 {offset_minutes():+d} 分钟" if offset_minutes() else ""
    return f"{tz_name()} (UTC{sign}{extra})"


def use_fake(dt):
    """测试用：把「现在」冻结到指定时间（生产不要调）"""
    _FAKE["value"] = dt
    return dt


def reset():
    """恢复真实时间"""
    _FAKE["value"] = None
