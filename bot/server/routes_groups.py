# ===================== 自建群聊 API（v35.9.0.4） =====================
from __future__ import annotations

from ..infra import repo_groups, tenant
from .common import json_response


async def handle_list(request):
    rows = repo_groups.list_for(tenant.owner_id())
    return json_response({"ok": True, "data": rows, "count": len(rows)})


async def handle_create(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = str((body or {}).get("name") or "").strip()
    if not name:
        return json_response({"ok": False, "error": "bad_name", "message": "群名不能为空"}, 400)
    members = (body or {}).get("members") or []
    if not isinstance(members, list):
        return json_response({"ok": False, "error": "bad_members"}, 400)
    try:
        row = repo_groups.create(tenant.owner_id(), name, members)
        return json_response({"ok": True, **row, "type": "group"})
    except Exception as exc:
        return json_response({"ok": False, "error": "create_failed", "message": str(exc)}, 500)
