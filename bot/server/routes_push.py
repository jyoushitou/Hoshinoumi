# ===================== ntfy / UnifiedPush 设备与 outbox（v35.8.4.x） =====================
# 自托管 ntfy：设备注册、偏好、outbox、去重、重试、测试推送。
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
DEVICES_FILE = ROOT / "data" / "push_devices.json"
OUTBOX_FILE = ROOT / "data" / "push_outbox.json"
_LOCK = threading.Lock()


def _load(path, fallback):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, type(fallback)) else fallback
    except Exception:
        return fallback


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _devices():
    return [x for x in _load(DEVICES_FILE, []) if isinstance(x, dict) and x.get("id")]


def _outbox():
    return [x for x in _load(OUTBOX_FILE, []) if isinstance(x, dict) and x.get("id")]


def _prefs(device):
    return {"messages": True, "reminders": True, "dnd": False, **(device.get("preferences") or {})}


def _public(device):
    return {
        "id": device["id"], "platform": device.get("platform") or "android",
        "topic": device.get("topic") or "", "endpoint": device.get("endpoint") or "",
        "enabled": bool(device.get("enabled", True)), "preferences": _prefs(device),
        "created_at": device.get("created_at") or "",
    }


def _publish(entry):
    """向 ntfy endpoint POST JSON；返回 (ok, status, error)。"""
    endpoint = str(entry.get("endpoint") or "").strip()
    if not endpoint:
        return False, 0, "missing endpoint"
    payload = json.dumps({
        "title": entry.get("title") or "Hoshinoumi",
        "message": entry.get("message") or "",
        "click": entry.get("click") or "/chat",
        "priority": 3,
        "tags": ["hoshinoumi"],
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "HoshinoumiPush/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300, response.status, ""
    except Exception as exc:
        return False, 0, str(exc)


def notify(title, message, click="/chat", key=None):
    """把通知写入 outbox 并立即投递；同一 key 去重。返回投递结果。"""
    key = str(key or uuid.uuid4().hex)
    results = []
    with _LOCK:
        devices = [x for x in _devices() if x.get("enabled", True) and _prefs(x).get("messages", True)]
        outbox = _outbox()
        if any(x.get("key") == key for x in outbox):
            return {"ok": True, "deduped": True, "delivered": 0}
        for device in devices:
            if _prefs(device).get("dnd"):
                continue
            entry = {"id": uuid.uuid4().hex, "key": key, "device_id": device["id"],
                     "title": title, "message": message, "click": click,
                     "endpoint": device.get("endpoint"), "attempts": 0,
                     "status": "pending", "created_at": datetime.now().isoformat(timespec="seconds")}
            for attempt in range(3):
                entry["attempts"] = attempt + 1
                ok, status, error = _publish(entry)
                if ok:
                    entry["status"] = "delivered"; entry["http_status"] = status; break
                entry["status"] = "failed"; entry["last_error"] = error
                time.sleep(0.4 * (attempt + 1))
            outbox.append(entry)
            results.append({"device_id": device["id"], "status": entry["status"], "attempts": entry["attempts"]})
        _save(OUTBOX_FILE, outbox[-200:])
    return {"ok": True, "deduped": False, "delivered": len([x for x in results if x["status"] == "delivered"]), "results": results}


async def handle_devices(request):
    return json_response({"ok": True, "data": [_public(x) for x in _devices()]})


async def handle_register(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    topic = str(body.get("topic") or "").strip()
    endpoint = str(body.get("endpoint") or "").strip()
    if not topic or not endpoint.startswith(("http://", "https://")):
        return json_response({"ok": False, "error": "bad_device", "message": "topic 和 http(s) endpoint 必填"}, 400)
    with _LOCK:
        devices = _devices()
        existing = next((x for x in devices if x.get("topic") == topic and x.get("endpoint") == endpoint), None)
        if existing:
            existing["platform"] = str(body.get("platform") or existing.get("platform") or "android")
            device = existing
        else:
            device = {"id": "dev_" + uuid.uuid4().hex[:12], "platform": str(body.get("platform") or "android"),
                      "topic": topic, "endpoint": endpoint, "enabled": True,
                      "preferences": {"messages": True, "reminders": True, "dnd": False},
                      "created_at": datetime.now().isoformat(timespec="seconds")}
            devices.append(device)
        _save(DEVICES_FILE, devices)
    return json_response({"ok": True, "data": _public(device)})


async def handle_delete(request):
    device_id = request.match_info.get("id", "")
    with _LOCK:
        devices = _devices()
        remain = [x for x in devices if x.get("id") != device_id]
        if len(remain) == len(devices):
            return json_response({"ok": False, "error": "device_not_found"}, 404)
        _save(DEVICES_FILE, remain)
    return json_response({"ok": True, "deleted": device_id})


async def handle_preferences(request):
    if request.method == "PATCH":
        try:
            body = await request.json()
        except Exception:
            return json_response({"ok": False, "error": "invalid_json"}, 400)
        with _LOCK:
            devices = _devices()
            if not devices:
                return json_response({"ok": False, "error": "device_not_found"}, 404)
            device = devices[0]
            device["preferences"] = {**_prefs(device), **{k: bool(body[k]) for k in ("messages", "reminders", "dnd") if k in body}}
            _save(DEVICES_FILE, devices)
        return json_response({"ok": True, "preferences": device["preferences"]})
    devices = _devices()
    return json_response({"ok": True, "preferences": _prefs(devices[0]) if devices else {"messages": True, "reminders": True, "dnd": False}})


async def handle_test(request):
    result = notify("Hoshinoumi 测试通知", "这是一条 5 分钟测试通知。", "/chat", key="test:" + str(int(time.time())))
    return json_response({"ok": bool(result.get("ok")), "data": result})


async def handle_outbox(request):
    rows = list(reversed(_outbox()))[-50:]
    return json_response({"ok": True, "data": rows, "count": len(rows)})
