# ===================== 周计划表 API（v35.2.21/22） =====================
from __future__ import annotations

from ..life import weekly_plan
from ..infra import tenant
from .common import json_response


def _uid(request=None):
    return tenant.owner_id()


def _week(raw, default=1):
    try:
        n = int(raw)
    except Exception:
        n = default
    return max(1, min(n, 60))


def _valid_courses(courses):
    if not isinstance(courses, list):
        raise ValueError("courses must be an array")
    out = []
    for x in courses:
        if not isinstance(x, dict):
            continue
        name = str(x.get("name") or "").strip()[:200]
        if not name:
            continue
        try:
            weekday = int(x.get("weekday") or 1)
            p0 = int(x.get("period_start") or 1)
            p1 = int(x.get("period_end") or p0)
        except Exception:
            continue
        out.append({
            "name": name,
            "teacher": str(x.get("teacher") or "")[:200],
            "location": str(x.get("location") or "")[:200],
            "weekday": max(1, min(weekday, 7)),
            "weekday_name": weekly_plan.WEEKDAYS[max(1, min(weekday, 7)) - 1],
            "period_start": max(1, min(p0, 11)),
            "period_end": max(1, min(p1, 11)),
            "weeks_raw": str(x.get("weeks_raw") or "")[:200],
            "weeks": [int(w) for w in (x.get("weeks") or []) if str(w).isdigit()][:60],
            "start_week": x.get("start_week"),
            "end_week": x.get("end_week"),
            "source": str(x.get("source") or "manual")[:32],
        })
    return out


async def handle_weekly_weeks(request):
    weeks = weekly_plan.list_weeks(_uid(request))
    return json_response({"ok": True, "weeks": weeks})


async def handle_weekly_get(request):
    week = _week(request.query.get("week", 1))
    data = weekly_plan.load_week(_uid(request), week)
    return json_response({"ok": True, "week": week, "courses": data, "count": len(data)})


async def handle_weekly_put(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    week = _week((body or {}).get("week", 1))
    try:
        courses = _valid_courses((body or {}).get("courses"))
    except Exception as e:
        return json_response({"ok": False, "error": "invalid_courses", "message": str(e)}, 400)
    try:
        weekly_plan.save_week(_uid(request), week, courses)
        return json_response({"ok": True, "week": week, "count": len(courses)})
    except Exception as e:
        return json_response({"ok": False, "error": "save_failed", "message": str(e)}, 500)


async def handle_weekly_import(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    if not isinstance(body, dict):
        return json_response({"ok": False, "error": "invalid_body"}, 400)
    week = _week(body.get("week", 1))
    html_text = body.get("html")
    if not isinstance(html_text, str) or not html_text.strip():
        return json_response({"ok": False, "error": "html_required"}, 400)
    try:
        rows, total = weekly_plan.import_html(_uid(request), html_text, week, dry_run=bool(body.get("dry_run")))
        return json_response({"ok": True, "week": week, "count": len(rows), "all_weeks_count": total,
                              "dry_run": bool(body.get("dry_run")), "courses": rows[:100]})
    except Exception as e:
        return json_response({"ok": False, "error": "import_failed", "message": str(e)}, 500)
