# ===================== 健康 / 热量 API（v35.9.6.7） =====================
# 本机文件存储，只服务当前 owner；识图未接视觉模型时明确返回未配置。
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
HEALTH_FILE = ROOT / "data" / "health.json"
_LOCK = threading.Lock()
_DEFAULT = {"target": 2000, "burn": 320, "weight": 52.4, "meals": [], "initialized": False}


def _load():
    try:
        data = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**_DEFAULT, **data, "meals": list(data.get("meals") or [])}
    except Exception:
        pass
    return json.loads(json.dumps(_DEFAULT))


def _save(data):
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(HEALTH_FILE)


def _payload(data):
    intake = sum(int(x.get("kcal") or 0) for x in data.get("meals", []))
    return {"ok": True, "data": data, "intake": intake, "remaining": int(data.get("target", 0)) + int(data.get("burn", 0)) - intake}


async def handle_summary(request):
    data = _load()
    return json_response(_payload(data))


async def handle_add_meal(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = str(body.get("name") or "").strip()[:80]
    try:
        kcal = int(body.get("kcal") or 0)
    except (TypeError, ValueError):
        kcal = 0
    if not name or kcal <= 0:
        return json_response({"ok": False, "error": "bad_meal", "message": "食物名和热量必填"}, 400)
    with _LOCK:
        data = _load()
        meal = {"id": int(datetime.now().timestamp() * 1000), "name": name, "kcal": kcal, "time": datetime.now().strftime("%H:%M")}
        data["meals"].append(meal)
        _save(data)
    return json_response({"ok": True, "data": meal, **_payload(data)})


async def handle_delete_meal(request):
    try:
        meal_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    with _LOCK:
        data = _load()
        before = len(data["meals"])
        data["meals"] = [x for x in data["meals"] if int(x.get("id") or 0) != meal_id]
        if len(data["meals"]) == before:
            return json_response({"ok": False, "error": "meal_not_found"}, 404)
        _save(data)
    return json_response({"ok": True, "deleted": meal_id})


async def handle_recognize(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    image = str(body.get("data_base64") or "")
    if not image:
        return json_response({"ok": False, "error": "missing_image", "message": "缺少图片"}, 400)
    if len(image) > 12 * 1024 * 1024:
        return json_response({"ok": False, "error": "image_too_large"}, 413)
    return json_response({
        "ok": False,
        "error": "vision_not_configured",
        "message": "视觉识别模型尚未配置，请手动填写食物与热量",
    }, 501)

async def handle_init_get(request):
    data = _load()
    return json_response({"ok": True, "initialized": bool(data.get("initialized")),
                          "target": data.get("target", 2000), "burn": data.get("burn", 320),
                          "weight": data.get("weight", 52.4)})


async def handle_init_post(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    with _LOCK:
        data = _load()
        try:
            target = int((body or {}).get("target") or data.get("target", 2000))
            burn = int((body or {}).get("burn") or data.get("burn", 320))
            weight = float((body or {}).get("weight") or data.get("weight", 52.4))
        except (TypeError, ValueError):
            return json_response({"ok": False, "error": "bad_values"}, 400)
        if target < 0 or burn < 0 or weight <= 0:
            return json_response({"ok": False, "error": "bad_values"}, 400)
        data.update({"target": target, "burn": burn, "weight": round(weight, 1), "initialized": True})
        _save(data)
    return json_response({"ok": True, "initialized": True, "target": target, "burn": burn, "weight": round(weight, 1)})
