# ===================== 学习计划 API（v34.0.1） =====================
# GET /api/plan、POST /api/plan、POST /api/plan/import、GET /api/plan/export

from ..life import study_plan
from ..core import tenant
from .common import json_response


def _uid(request):
    return tenant.owner_id()


async def handle_get(request):
    week = request.query.get("week_start") or ""
    try:
        return json_response(study_plan.load_week(_uid(request), week))
    except Exception as e:
        return json_response({"error": "invalid_week", "message": str(e)}, 400)


async def handle_put(request):
    try:
        body = await request.json()
        return json_response(study_plan.save_week(_uid(request), body))
    except Exception as e:
        return json_response({"error": "invalid_plan", "message": str(e)}, 400)


async def handle_import(request):
    try:
        body = await request.json()
        text = body.get("json") if isinstance(body, dict) else body
        return json_response(study_plan.import_text(_uid(request), text))
    except Exception as e:
        return json_response({"error": "invalid_plan", "message": str(e)}, 400)


async def handle_export(request):
    week = request.query.get("week_start") or ""
    try:
        return json_response({"json": study_plan.export_text(_uid(request), week)})
    except Exception as e:
        return json_response({"error": "invalid_week", "message": str(e)}, 400)
