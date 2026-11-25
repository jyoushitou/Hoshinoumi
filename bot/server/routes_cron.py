# ===================== 定时任务公开 API（v35.9.24.0） =====================
# Web / 手机 / 套壳共用：列表、增、改、删、启停、立即运行。
from __future__ import annotations

from aiohttp import web

from ..infra import tenant
from ..schedule import cron
from .common import json_response

TYPES = {"daily", "hourly", "weekly", "once", "interval", "scene"}


def _target():
    return str(tenant.owner_id())


def _row(task):
    return {
        "id": task.get("id"),
        "schedule_type": task.get("schedule_type"),
        "content": task.get("content"),
        "at_time": task.get("at_time"),
        "weekdays": task.get("weekdays"),
        "once_at": str(task.get("once_at")) if task.get("once_at") else None,
        "interval_min": task.get("interval_min"),
        "rule": task.get("rule"),
        "timing": task.get("timing"),
        "enabled": bool(task.get("enabled")),
        "last_fire": str(task.get("last_fire")) if task.get("last_fire") else None,
        "next_ts": str(task.get("next_ts")) if task.get("next_ts") else None,
    }


async def handle_list(request):
    rows = cron.list_tasks(_target(), user_id="__owner__")
    return json_response({"ok": True, "data": [_row(x) for x in rows], "count": len(rows)})


async def handle_create(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    content = str(body.get("content") or "").strip()[:100]
    schedule_type = str(body.get("schedule_type") or "daily").strip()
    if not content:
        return json_response({"ok": False, "error": "content_required"}, 400)
    if schedule_type not in TYPES:
        return json_response({"ok": False, "error": "bad_schedule"}, 400)
    at_time = str(body.get("at_time") or "08:00").strip()[:20]
    weekdays = body.get("weekdays") if isinstance(body.get("weekdays"), str) else None
    task_id = cron.add(_target(), schedule_type, content, at_time=at_time, weekdays=weekdays, source="api", user_id="__owner__")
    if not task_id:
        return json_response({"ok": False, "error": "create_failed"}, 400)
    try:
        cron.schedule_all()
    except Exception:
        pass
    return json_response({"ok": True, "data": _row(cron.get(task_id))})


async def handle_update(request):
    try:
        task_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    task = cron.get(task_id)
    if not task:
        return json_response({"ok": False, "error": "task_not_found"}, 404)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    fields = {}
    if "enabled" in body:
        fields["enabled"] = 1 if body["enabled"] else 0
    if "content" in body:
        content = str(body["content"]).strip()[:100]
        if not content:
            return json_response({"ok": False, "error": "content_required"}, 400)
        fields["content"] = content
    if "at_time" in body:
        fields["at_time"] = str(body["at_time"]).strip()[:20]
    if "schedule_type" in body:
        if body["schedule_type"] not in TYPES:
            return json_response({"ok": False, "error": "bad_schedule"}, 400)
        fields["schedule_type"] = body["schedule_type"]
    ok = cron.update(task_id, user_id="__owner__", **fields)
    if not ok:
        return json_response({"ok": False, "error": "update_failed"}, 400)
    try:
        cron.schedule_all()
    except Exception:
        pass
    return json_response({"ok": True, "data": _row(cron.get(task_id))})


async def handle_delete(request):
    try:
        task_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    task = cron.get(task_id)
    if not task:
        return json_response({"ok": False, "error": "task_not_found"}, 404)
    cron.cancel(task_id)
    cron.remove(task_id)
    return json_response({"ok": True, "deleted": task_id})


async def handle_run(request):
    try:
        task_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    task = cron.get(task_id)
    if not task:
        return json_response({"ok": False, "error": "task_not_found"}, 404)
    if not int(task.get("enabled") or 0):
        return json_response({"ok": False, "error": "disabled", "message": "任务已停用"}, 409)
    try:
        from ..scheduler.dispatcher import get_scheduler
        get_scheduler().submit("cron_task", f"cron-manual:{task_id}", args=(task_id,))
    except Exception as exc:
        return json_response({"ok": False, "error": "run_failed", "message": str(exc)}, 500)
    return json_response({"ok": True, "queued": True, "task_id": task_id})
