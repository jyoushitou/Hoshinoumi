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


def now(tz=CST):
    """当前时间（默认带东八区时区）"""
    return datetime.now(tz)


def naive():
    """当前北京时间的墙钟值（naive，用于和解析出的字符串时间做算术）"""
    return datetime.now(CST).replace(tzinfo=None)


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
