# ===================== 健康 / 热量 API（v35.9.38） =====================
# BMR 按体重估算；目标按当前体重、目标体重、月数自动算；运动热量按 MET*体重*时长。
from __future__ import annotations

import base64
import json
import threading
from datetime import datetime
from pathlib import Path

from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
HEALTH_FILE = ROOT / "data" / "health.json"
_LOCK = threading.Lock()

_DEFAULT = {
    "current_weight": 52.4,
    "target_weight": 50.0,
    "months": 3,
    "meals": [],
    "exercises": [],
    "initialized": False,
}

_MET = {"走路": 3.5, "跑步": 8.0, "骑行": 6.0, "力量": 5.0, "瑜伽": 2.5, "其他": 4.0}


def _load():
    try:
        data = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "current_weight" not in data and "weight" in data:
                data["current_weight"] = data.get("weight")
            return {**_DEFAULT, **data,
                    "meals": list(data.get("meals") or []),
                    "exercises": list(data.get("exercises") or [])}
    except Exception:
        pass
    return json.loads(json.dumps(_DEFAULT))


def _save(data):
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(HEALTH_FILE)


def _bmr(weight):
    return max(800, int(round(float(weight or 0) * 22)))


def _target_kcal(weight, target_weight, months):
    bmr = _bmr(weight)
    days = max(30, int(months or 1) * 30)
    delta = (float(weight or 0) - float(target_weight or 0)) * 7700 / days
    return max(800, int(round(bmr - delta)))


def _exercise_kcal(kind, minutes, weight):
    met = _MET.get(str(kind or "其他"), 4.0)
    return max(0, int(round(met * float(weight or 0) * max(0, int(minutes or 0)) / 60)))


def _payload(data):
    intake = sum(int(x.get("kcal") or 0) for x in data.get("meals", []))
    exercise = sum(int(x.get("kcal") or 0) for x in data.get("exercises", []))
    weight = float(data.get("current_weight") or 0)
    target = _target_kcal(weight, data.get("target_weight"), data.get("months"))
    return {
        "ok": True,
        "data": {**data, "bmr": _bmr(weight), "target_kcal": target, "exercise_kcal": exercise},
        "intake": intake,
        "exercise": exercise,
        "remaining": target + exercise - intake,
    }


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


async def handle_add_exercise(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    kind = str(body.get("kind") or "其他")
    try:
        minutes = int(body.get("minutes") or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return json_response({"ok": False, "error": "bad_minutes"}, 400)
    with _LOCK:
        data = _load()
        kcal = _exercise_kcal(kind, minutes, data.get("current_weight"))
        item = {"id": int(datetime.now().timestamp() * 1000), "kind": kind, "minutes": minutes,
                "kcal": kcal, "time": datetime.now().strftime("%H:%M")}
        data["exercises"].append(item)
        _save(data)
    return json_response({"ok": True, "data": item, **_payload(data)})


async def handle_delete_exercise(request):
    try:
        item_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    with _LOCK:
        data = _load()
        before = len(data["exercises"])
        data["exercises"] = [x for x in data["exercises"] if int(x.get("id") or 0) != item_id]
        if len(data["exercises"]) == before:
            return json_response({"ok": False, "error": "exercise_not_found"}, 404)
        _save(data)
    return json_response({"ok": True, "deleted": item_id})


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
    try:
        raw = base64.b64decode(image.split(",", 1)[-1])
        from ..ai.vision import describe_image
        prompt = ("识别这张图片里的食物。只输出两行：\n"
                  "食物：<食物名>\n热量：<估算 kcal 数字>\n不要输出其他内容。")
        desc, _tags = await describe_image(raw, prompt=prompt, max_tokens=120)
        if not desc:
            return json_response({"ok": False, "error": "vision_not_configured",
                                  "message": "视觉模型不可用或未配置，请手动填写"}, 501)
        import re
        food = ""
        kcal = 0
        fm = re.search(r"食物\s*[:：]\s*(.+)", desc)
        km = re.search(r"热量\s*[:：]\s*(\d+)", desc)
        if fm:
            food = fm.group(1).strip().splitlines()[0][:60]
        if km:
            kcal = int(km.group(1))
        if not food or kcal <= 0:
            return json_response({"ok": False, "error": "recognition_failed",
                                  "message": "模型没有返回食物热量，请手动填写"}, 502)
        return json_response({"ok": True, "food": food, "kcal": kcal, "raw": desc})
    except Exception as e:
        return json_response({"ok": False, "error": "vision_failed", "message": str(e)}, 502)


async def handle_init_get(request):
    data = _load()
    return json_response({"ok": True, "initialized": bool(data.get("initialized")),
                          "current_weight": data.get("current_weight", 52.4),
                          "target_weight": data.get("target_weight", 50.0),
                          "months": data.get("months", 3),
                          "bmr": _bmr(data.get("current_weight")),
                          "target_kcal": _target_kcal(data.get("current_weight"), data.get("target_weight"), data.get("months"))})


async def handle_init_post(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    with _LOCK:
        data = _load()
        try:
            current = float((body or {}).get("current_weight"))
            target = float((body or {}).get("target_weight"))
            months = int((body or {}).get("months"))
        except (TypeError, ValueError):
            return json_response({"ok": False, "error": "bad_values"}, 400)
        if current <= 0 or target <= 0 or months <= 0:
            return json_response({"ok": False, "error": "bad_values"}, 400)
        data.update({"current_weight": round(current, 1), "target_weight": round(target, 1),
                     "months": months, "initialized": True})
        _save(data)
    return json_response({"ok": True, "initialized": True,
                          "current_weight": round(current, 1), "target_weight": round(target, 1),
                          "months": months, "bmr": _bmr(current),
                          "target_kcal": _target_kcal(current, target, months)})
