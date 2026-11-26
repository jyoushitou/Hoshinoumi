# ===================== 聊天模式（v35.9.33） =====================
# chat / code / agent / shell 四选一，owner-only，code 30 分钟超时。
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..config import MASTER_QQ
from ..infra import tenant
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data" / "chat_mode.json"
CODE_TIMEOUT = 30 * 60
MODES = {
    "chat": {"label": "Chat", "description": "普通聊天"},
    "code": {"label": "Code", "description": "独立代码会话，共享记忆", "timeout": CODE_TIMEOUT},
    "agent": {"label": "Agent", "description": "工具调用与任务状态"},
    "shell": {"label": "Shell", "description": "危险命令审批与输出"},
}


def _owner(request):
    return str(tenant.owner_id()) == str(MASTER_QQ)


def _load():
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"mode": "chat", "updated_at": "", "expires_at": None, "agent_task": "", "approval": None}


def _save(data):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize(data):
    now = time.time()
    if data.get("mode") == "code" and data.get("expires_ts") and data["expires_ts"] < now:
        data.update({"mode": "chat", "expires_at": None, "expires_ts": None, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        _save(data)
    return data


def _public(data):
    mode = data.get("mode") if data.get("mode") in MODES else "chat"
    return {
        "mode": mode,
        "label": MODES[mode]["label"],
        "description": MODES[mode]["description"],
        "modes": [{"id": key, **value} for key, value in MODES.items()],
        "updated_at": data.get("updated_at") or "",
        "expires_at": data.get("expires_at"),
        "expires_in": max(0, int(data.get("expires_ts") or 0) - int(time.time())) if mode == "code" else None,
        "agent_task": data.get("agent_task") or "",
        "approval": data.get("approval"),
    }


async def handle_chat_mode_get(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    return json_response({"ok": True, "data": _public(_normalize(_load()))})


async def handle_chat_mode_set(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    mode = str(body.get("mode") or "").strip().lower()
    if mode not in MODES:
        return json_response({"ok": False, "error": "bad_mode"}, 400)
    data = _normalize(_load())
    data["mode"] = mode
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if mode == "code":
        data["expires_ts"] = int(time.time()) + CODE_TIMEOUT
        data["expires_at"] = (datetime.now() + timedelta(seconds=CODE_TIMEOUT)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        data["expires_ts"] = None
        data["expires_at"] = None
    if mode != "agent":
        data["agent_task"] = ""
    if mode != "shell":
        data["approval"] = None
    _save(data)
    return json_response({"ok": True, "data": _public(data)})


async def handle_chat_mode_approve(request):
    if not _owner(request):
        return json_response({"ok": False, "error": "owner_only"}, 403)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    data = _normalize(_load())
    if data.get("mode") != "shell":
        return json_response({"ok": False, "error": "not_shell_mode"}, 409)
    data["approval"] = {
        "command": str(body.get("command") or "").strip()[:500],
        "approved": bool(body.get("approved")),
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save(data)
    return json_response({"ok": True, "data": _public(data)})
