# ===================== API 余额（v35.2.23.0） =====================
# DeepSeek /user/balance；没有 key/请求失败都返回未知，不伪造。
from __future__ import annotations

import time

from ..core import state as cfg
from ..infra.blocking import run_blocking
from .common import json_response

BALANCE_URL = "https://api.deepseek.com/user/balance"
_cache = {"ts": 0.0, "data": None}
CACHE_SECONDS = 60


def _fetch():
    import requests
    key = (getattr(cfg, "DS_API_KEY", "") or "").strip()
    if not key:
        return {"ok": False, "error": "no_key", "message": "未配置 DeepSeek API key"}
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    r = requests.get(BALANCE_URL, headers=headers, timeout=(5, 10), verify=False)
    try:
        data = r.json()
    except Exception:
        data = {}
    if r.status_code != 200:
        return {"ok": False, "error": "http_" + str(r.status_code), "message": str(data)[:300]}
    infos = data.get("balance_infos") if isinstance(data, dict) else None
    if not isinstance(infos, list):
        infos = []
    return {
        "ok": True,
        "is_available": bool(data.get("is_available")),
        "balance_infos": infos,
    }


async def handle_balance(request):
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < CACHE_SECONDS:
        return json_response(_cache["data"])
    try:
        data = await run_blocking(_fetch, timeout=15, name="deepseek_balance")
    except Exception as e:
        data = {"ok": False, "error": "failed", "message": str(e)}
    data["fetched_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _cache["ts"] = now
    _cache["data"] = data
    return json_response(data)
