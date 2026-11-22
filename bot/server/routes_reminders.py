# ===================== 提醒队列 API（v35.7.1.1） =====================
from __future__ import annotations

from ..infra import repo_reminders, tenant
from .common import json_response


def _uid(request=None):
    return tenant.owner_id()


async def handle_pending(request):
    rows = repo_reminders.pending(_uid(request), limit=request.query.get("limit", 20))
    return json_response({"ok": True, "reminders": rows})


async def handle_ack(request):
    try:
        reminder_id = int(request.match_info.get("id") or 0)
    except Exception:
        return json_response({"ok": False, "error": "bad_id"}, 400)
    if reminder_id <= 0:
        return json_response({"ok": False, "error": "bad_id"}, 400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = str((body or {}).get("action") or "done").strip().lower()
    if action not in ("done", "later"):
        return json_response({"ok": False, "error": "bad_action"}, 400)
    ok = repo_reminders.ack(reminder_id, action, _uid(request))
    return json_response({"ok": ok}, 200 if ok else 404)
