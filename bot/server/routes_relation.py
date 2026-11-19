# ===================== 关系 API（v35.2.25.0） =====================
from __future__ import annotations

from ..core import state as cfg
from ..infra import tenant
from ..life import relation
from .common import json_response


def _viewer(request):
    """本地 owner token 默认 owner；网关可带 X-User-Id 表示普通用户。"""
    raw = (request.headers.get("X-User-Id") or request.query.get("user_id") or "").strip()
    if raw:
        return raw, tenant.is_owner(raw)
    return tenant.owner_id(), True


def _target(request, viewer, can_view_all):
    if not can_view_all:
        return viewer
    raw = (request.query.get("target_id") or "").strip()
    if raw:
        return raw
    try:
        return str(cfg.MASTER_QQ)
    except Exception:
        return viewer


async def handle_relation(request):
    viewer, can_view_all = _viewer(request)
    tid = _target(request, viewer, can_view_all)
    try:
        aff = relation.get(tid, user_id=viewer)
        tier, desc = relation.tier_of(aff)
        events = relation.recent_events(tid, user_id=viewer, limit=20)
        return json_response({
            "ok": True,
            "viewer": viewer,
            "can_view_all": bool(can_view_all),
            "target_id": tid,
            "affinity": round(float(aff), 3),
            "tier": tier,
            "description": desc,
            "events": [dict(x) for x in events],
        })
    except Exception as e:
        return json_response({"ok": False, "error": "relation_failed", "message": str(e)}, 500)
