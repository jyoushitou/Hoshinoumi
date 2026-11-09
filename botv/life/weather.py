# ===================== 天气（v12-A21） =====================
# 用 wttr.in 的免费 JSON 接口（不需要 key）。没配城市就不查。
#
# 环境变量：NAO_CITY=Tokyo（中文城市名也认）
# 缓存 30 分钟，失败就当没有，绝不影响回复。

import os
import time as _time

from ..log import log_api

DEFAULT_TIMEOUT = 6
CACHE_SECONDS = 1800

_cache = {"ts": 0.0, "data": None}


def city():
    return os.getenv("NAO_CITY", "").strip()


def parse_j1(data):
    """从 wttr.in 的 j1 输出里取 (温度, 天气描述)"""
    try:
        cur = data["current_condition"][0]
        temp = int(cur["temp_C"])
        desc = cur["weatherDesc"][0]["value"]
        return {"temp": temp, "desc": desc}
    except Exception:
        return None


def describe(info):
    """给 prompt 用的一句话"""
    if not info:
        return ""
    return f"（外面 {info['temp']}°C，{info['desc']}）"


async def current(force=False):
    """返回 {'temp':..,'desc':..}；没配城市或失败返回 None"""
    if not city():
        return None
    now = _time.time()
    if not force and _cache["data"] and now - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]

    try:
        import asyncio
        import requests

        url = f"https://wttr.in/{city()}?format=j1"

        def _get():
            s = requests.Session()
            try:
                return s.get(url, timeout=DEFAULT_TIMEOUT,
                             headers={"User-Agent": "curl/8"})
            finally:
                s.close()

        resp = await asyncio.to_thread(_get)
        if resp.status_code != 200:
            log_api(f"[天气] 失败 {resp.status_code}")
            return None
        info = parse_j1(resp.json())
        if info:
            _cache["ts"] = now
            _cache["data"] = info
            log_api(f"[天气] {info['temp']}°C {info['desc']}")
        return info
    except Exception as e:
        log_api(f"[天气] 异常: {e}")
        return None
