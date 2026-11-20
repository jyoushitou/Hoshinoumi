# ===================== QQ 头像缓存（v35.5） =====================
# 前端不直接访问 qlogo：后端拉取后落盘，Web 读 /api/avatar。
# 每天 04:00 由 HTTP 服务后台任务刷新一次；失败保留旧图。

import asyncio
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

_DIR = Path("data/avatars")
_INDEX = _DIR / "index.json"
_TTL = 24 * 3600
_UA = "Mozilla/5.0 HoshinoumiAvatar/1.0"


def _safe(kind, ident):
    s = re.sub(r"[^0-9A-Za-z_.-]", "", str(ident or ""))
    return f"{kind}_{s}" if s else ""


def _read_index():
    if not _INDEX.exists():
        return {}
    try:
        return json.loads(_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_index(data):
    _DIR.mkdir(parents=True, exist_ok=True)
    tmp = _INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_INDEX)


def _url(kind, ident):
    q = urllib.parse.quote(str(ident))
    if kind == "group":
        return f"https://p.qlogo.cn/gh/{q}/{q}/100"
    return f"https://q1.qlogo.cn/g?b=qq&nk={q}&s=100"


def _fetch(kind, ident):
    req = urllib.request.Request(_url(kind, ident), headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read(2 * 1024 * 1024)
        ctype = (r.headers.get("Content-Type") or "image/jpeg").split(";")[0]
    if not body:
        raise ValueError("empty avatar")
    return body, ctype


def resolve(kind, ident, force=False):
    """返回 (bytes|None, content_type)。优先本地缓存，过期刷新，失败回退旧文件。"""
    key = _safe(kind, ident)
    if not key:
        return None, "image/jpeg"
    path = _DIR / (key + ".bin")
    idx = _read_index()
    row = idx.get(key) or {}
    fresh = path.exists() and time.time() - float(row.get("ts") or 0) < _TTL
    if fresh and not force:
        return path.read_bytes(), row.get("type") or "image/jpeg"
    try:
        body, ctype = _fetch(kind, ident)
        _DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        idx[key] = {"kind": kind, "id": str(ident), "ts": time.time(), "type": ctype}
        _write_index(idx)
        return body, ctype
    except Exception:
        if path.exists():
            return path.read_bytes(), (idx.get(key) or {}).get("type") or "image/jpeg"
        return None, "image/jpeg"


async def loop_daily(hour=4, minute=0):
    """HTTP 服务启动后后台跑：每天固定时间刷新全部缓存。"""
    while True:
        now = time.localtime()
        target = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hour, minute, 0, 0, 0, -1))
        if target <= time.time():
            target += 86400
        await asyncio.sleep(max(60, target - time.time()))
        await asyncio.to_thread(refresh_all)


def refresh_all():
    idx = _read_index()
    for key, row in list(idx.items()):
        try:
            resolve(row.get("kind") or "qq", row.get("id") or key, force=True)
        except Exception:
            pass
