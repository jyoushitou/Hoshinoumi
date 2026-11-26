# ===================== 会话偏好 / 群管理（v35.9.35） =====================
from __future__ import annotations

from datetime import datetime

from ..config import MASTER_QQ
from ..infra import tenant
from .common import json_response


def _uid(request=None):
    return str(tenant.owner_id())


def _owner(request):
    return _uid(request) == str(MASTER_QQ)


def _cursor():
    from ..infra.conn import get_cursor
    return get_cursor()


def _is_custom_group(target: str) -> bool:
    return str(target).startswith("h_")


def _group_owner(target: str) -> bool:
    if not _is_custom_group(target):
        return False
    c = _cursor()
    try:
        c.execute("SELECT 1 FROM custom_groups WHERE id=%s AND user_id=%s", (target, _uid()))
        return bool(c.fetchone())
    finally:
        try: c.close()
        except Exception: pass


async def handle_prefs(request):
    uid = _uid(request)
    c = _cursor()
    try:
        c.execute("SELECT target_id,muted,hidden,deleted_at,updated_at FROM conversation_preferences WHERE user_id=%s", (uid,))
        rows = c.fetchall() or []
        prefs = {str(r["target_id"]): {"muted": bool(r["muted"]), "hidden": bool(r["hidden"]),
                                       "deleted_at": str(r["deleted_at"]) if r["deleted_at"] else None,
                                       "updated_at": str(r["updated_at"]) if r["updated_at"] else None} for r in rows}
        return json_response({"ok": True, "data": prefs})
    finally:
        try: c.close()
        except Exception: pass


async def handle_pref_update(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    target = str(request.match_info.get("target") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "bad_target"}, 400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    muted = 1 if body.get("muted") else 0
    hidden = 1 if body.get("hidden") else 0
    uid = _uid(request)
    c = _cursor()
    try:
        if body.get("hidden") is None or body.get("muted") is None:
            c.execute("SELECT muted,hidden FROM conversation_preferences WHERE user_id=%s AND target_id=%s", (uid, target))
            row = c.fetchone()
            if row:
                if body.get("muted") is None: muted = int(row["muted"] or 0)
                if body.get("hidden") is None: hidden = int(row["hidden"] or 0)
        if _is_sqlite(c):
            c.execute("INSERT INTO conversation_preferences(user_id,target_id,muted,hidden,updated_at) VALUES(%s,%s,%s,%s,CURRENT_TIMESTAMP) "
                      "ON CONFLICT(user_id,target_id) DO UPDATE SET muted=excluded.muted,hidden=excluded.hidden,updated_at=CURRENT_TIMESTAMP",
                      (uid, target, muted, hidden))
        else:
            c.execute("INSERT INTO conversation_preferences(user_id,target_id,muted,hidden,updated_at) VALUES(%s,%s,%s,%s,CURRENT_TIMESTAMP) "
                      "ON DUPLICATE KEY UPDATE muted=VALUES(muted),hidden=VALUES(hidden),updated_at=CURRENT_TIMESTAMP",
                      (uid, target, muted, hidden))
        c.connection.commit()
        return json_response({"ok": True, "target_id": target, "muted": bool(muted), "hidden": bool(hidden)})
    finally:
        try: c.close()
        except Exception: pass


async def handle_conversation_delete(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    target = str(request.match_info.get("target") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "bad_target"}, 400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    dissolved = False
    uid = _uid(request)
    c = _cursor()
    try:
        if body.get("dissolve") and _is_custom_group(target):
            c.execute("DELETE FROM custom_groups WHERE id=%s AND user_id=%s", (target, uid))
            dissolved = True
        c.execute("INSERT INTO conversation_preferences(user_id,target_id,hidden,deleted_at,updated_at) VALUES(%s,%s,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) "
                  "ON CONFLICT(user_id,target_id) DO UPDATE SET hidden=1,deleted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP"
                  if _is_sqlite(c) else
                  "INSERT INTO conversation_preferences(user_id,target_id,hidden,deleted_at,updated_at) VALUES(%s,%s,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) "
                  "ON DUPLICATE KEY UPDATE hidden=1,deleted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP",
                  (uid, target))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return json_response({"ok": True, "target_id": target, "deleted": True, "dissolved": dissolved})


async def handle_group_admins(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    gid = str(request.match_info.get("id") or "").strip()
    if request.method == "GET":
        c = _cursor()
        try:
            c.execute("SELECT qq FROM group_admin_roles WHERE group_id=%s ORDER BY id", (gid,))
            admins = [str(r["qq"]) for r in (c.fetchall() or [])]
            return json_response({"ok": True, "group_id": gid, "owner": _uid(request), "admins": admins})
        finally:
            try: c.close()
            except Exception: pass
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    qq = str(body.get("qq") or "").strip()
    action = str(body.get("action") or "add")
    if not qq:
        return json_response({"ok": False, "error": "bad_qq"}, 400)
    c = _cursor()
    try:
        if action == "remove":
            c.execute("DELETE FROM group_admin_roles WHERE group_id=%s AND qq=%s", (gid, qq))
        else:
            c.execute("INSERT INTO group_admin_roles(group_id,qq) VALUES(%s,%s)" + (" ON CONFLICT(group_id,qq) DO NOTHING" if _is_sqlite(c) else " ON DUPLICATE KEY UPDATE qq=VALUES(qq)"), (gid, qq))
        c.connection.commit()
        c.execute("SELECT qq FROM group_admin_roles WHERE group_id=%s ORDER BY id", (gid,))
        admins = [str(r["qq"]) for r in (c.fetchall() or [])]
        return json_response({"ok": True, "group_id": gid, "admins": admins})
    finally:
        try: c.close()
        except Exception: pass


async def handle_group_settings_get(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    gid = str(request.match_info.get("id") or "").strip()
    return json_response({"ok": True, "group_id": gid, "recall_notice": recall_notice(gid)})


async def handle_group_settings(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    gid = str(request.match_info.get("id") or "").strip()
    try:
        body = await request.json()
    except Exception:
        body = {}
    notice = str(body.get("recall_notice") or "消息已撤回").strip()[:200] or "消息已撤回"
    c = _cursor()
    try:
        c.execute("INSERT INTO group_settings(group_id,recall_notice) VALUES(%s,%s)" + (" ON CONFLICT(group_id) DO UPDATE SET recall_notice=excluded.recall_notice" if _is_sqlite(c) else " ON DUPLICATE KEY UPDATE recall_notice=VALUES(recall_notice)"), (gid, notice))
        c.connection.commit()
        return json_response({"ok": True, "group_id": gid, "recall_notice": notice})
    finally:
        try: c.close()
        except Exception: pass


def recall_notice(target):
    c = _cursor()
    try:
        c.execute("SELECT recall_notice FROM group_settings WHERE group_id=%s", (str(target),))
        row = c.fetchone()
        return str(row["recall_notice"]) if row and row.get("recall_notice") else "消息已撤回"
    except Exception:
        return "消息已撤回"
    finally:
        try: c.close()
        except Exception: pass


def is_group_admin(target, qq):
    if str(qq) == str(MASTER_QQ):
        return True
    if _group_owner(str(target)):
        return True
    c = _cursor()
    try:
        c.execute("SELECT 1 FROM group_admin_roles WHERE group_id=%s AND qq=%s", (str(target), str(qq)))
        return bool(c.fetchone())
    finally:
        try: c.close()
        except Exception: pass


def _is_sqlite(cursor):
    try:
        return "sqlite" in str(type(cursor)).lower() or "sqlite" in str(getattr(cursor, "_cur", ""))
    except Exception:
        return True
