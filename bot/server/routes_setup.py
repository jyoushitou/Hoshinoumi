# ===================== 主人首次初始化（v35.9.37） =====================
from __future__ import annotations

from datetime import datetime

from ..infra import tenant
from .common import json_response


def _uid():
    return str(tenant.owner_id())


def _get_meta(c, key, default=""):
    c.execute("SELECT v FROM bot_meta WHERE k=%s", (key,))
    row = c.fetchone()
    return str(row.get("v") or default) if row else default


def _set_meta(c, key, value):
    from ..infra.conn import _resolve_backend
    if _resolve_backend() == "sqlite":
        c.execute("INSERT OR REPLACE INTO bot_meta(k,v,updated_at) VALUES(%s,%s,CURRENT_TIMESTAMP)", (key, value))
    else:
        c.execute("REPLACE INTO bot_meta(k,v,updated_at) VALUES(%s,%s,CURRENT_TIMESTAMP)", (key, value))


def _state(c, uid):
    from .routes_savings import _ensure_accounts
    _ensure_accounts(c, uid)
    c.execute("SELECT account FROM finance_accounts WHERE user_id=%s ORDER BY id", (uid,))
    accounts = [r["account"] for r in (c.fetchall() or [])]
    return {
        "initialized": _get_meta(c, "owner_initialized") == "1",
        "initialized_at": _get_meta(c, "owner_initialized_at"),
        "owner_id": uid,
        "accounts": accounts,
    }


async def handle_get(request):
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        return json_response({"ok": True, **_state(c, _uid())})
    finally:
        try: c.close()
        except Exception: pass


async def handle_init(request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    nickname = str((body or {}).get("nickname") or "").strip()[:40]
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        state = _state(c, _uid())
        if nickname:
            c.execute("UPDATE users SET nickname=%s WHERE id=%s", (nickname, _uid()))
        _set_meta(c, "owner_initialized", "1")
        _set_meta(c, "owner_initialized_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        try: c.connection.commit()
        except Exception: pass
        return json_response({"ok": True, "initialized": True, "nickname": nickname, "accounts": state["accounts"]})
    finally:
        try: c.close()
        except Exception: pass
