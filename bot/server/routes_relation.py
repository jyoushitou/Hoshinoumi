# ===================== 关系 API（v35.2.25.0） =====================
from __future__ import annotations

from ..core import state as cfg
from ..infra import tenant
from ..life import relation
from .common import json_response


def _target(request):
    raw = (request.query.get("target_id") or "").strip()
    if raw:
        return raw
    try:
        return str(cfg.MASTER_QQ)
    except Exception:
        return tenant.owner_id()


async def handle_relation(request):
    uid = tenant.owner_id()
    tid = _target(request)
    try:
        aff = relation.get(tid, user_id=uid)
        tier, desc = relation.tier_of(aff)
        events = relation.recent_events(tid, user_id=uid, limit=20)
        return json_response({
            "ok": True,
            "target_id": tid,
            "affinity": round(float(aff), 3),
            "tier": tier,
            "description": desc,
            "events": [dict(x) for x in events],
        })
    except Exception as e:
        return json_response({"ok": False, "error": "relation_failed", "message": str(e)}, 500)
