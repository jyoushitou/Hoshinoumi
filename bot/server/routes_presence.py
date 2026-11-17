# ===================== 主账号情境 API（v34.2） =====================

from ..life import presence
from ..infra import tenant
from .common import json_response


async def handle_get(request):
    return json_response(presence.get_presence(tenant.owner_id()) or {"activity": "unknown"})


async def handle_post(request):
    try:
        body = await request.json()
        presence.set_presence(tenant.owner_id(), body.get("activity"),
                              body.get("detail", ""), body.get("idle_min", 0),
                              body.get("source", "reporter"))
        return json_response({"ok": True})
    except Exception as e:
        return json_response({"error": "bad_presence", "message": str(e)}, 400)


async def handle_delete(request):
    presence.clear(tenant.owner_id())
    return json_response({"ok": True})
