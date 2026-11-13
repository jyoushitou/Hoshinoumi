# ===================== HTTP 服务器装配 =====================
# 鉴权中间件 + 路由注册 + 启动
# 迁移自 api_server.py（v5-R5）

import asyncio
import hmac

from aiohttp import web

from ..log import log_system
from . import config as apicfg
from .common import json_response
from .routes_meta import (
    handle_health, handle_status, handle_usage,
    handle_memory, handle_logs, handle_get_token,
)
from .routes_chat import handle_chat, handle_command


async def handle_internal_history(request):
    """v19.2：本机内部历史接口，读 conversation_messages"""
    from ..infra import repo_conversation

    target = (request.query.get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    try:
        limit = int(request.query.get("limit") or 100)
        before = int(request.query["before"]) if request.query.get("before") else None
    except ValueError:
        return json_response({"ok": False, "error": "bad limit/before"}, status=400)
    rows = repo_conversation.recent(
        target, limit=limit, before_id=before,
        user_id=request.query.get("user_id") or "__owner__",
    )
    data = []
    for r in rows:
        item = dict(r)
        if item.get("created_at") is not None:
            item["created_at"] = str(item["created_at"])
        data.append(item)
    return json_response({"ok": True, "data": data})


def _internal_uid(request):
    """网关已鉴权时用 X-Owner-Id；本机直连才回退 query。"""
    return (request.headers.get("X-Owner-Id")
            or request.query.get("user_id")
            or "__owner__").strip()


async def handle_internal_chat(request):
    """POST /internal/chat：网关转发 + 写入网关对话历史（v21.2）"""
    import uuid

    from ..ai.client import get_character_reply
    from ..infra import repo_conversation
    from ..log import log_err

    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "invalid_json", "message": "请求体必须是 JSON 格式"}, 400)

    message = body.get("message", "").strip()
    target_id = str(body.get("target_id", "")).strip()
    if not message:
        return json_response({"error": "empty_message", "message": "message 不能为空"}, 400)
    if not target_id:
        return json_response({"error": "missing_target_id", "message": "target_id 不能为空"}, 400)

    user_id = _internal_uid(request)
    client_id = str(body.get("client_message_id") or uuid.uuid4().hex)
    try:
        reply = await get_character_reply(message, target_id, body.get("keywords"))
        if not isinstance(reply, str) or not reply.strip():
            return json_response({"error": "empty_reply", "message": "AI 返回空回复"}, 500)

        # 只写成功的一轮；user/assistant 各自稳定 id，重试不会重复
        repo_conversation.append(
            user_id=user_id, target_id=target_id, content=message,
            role="user", channel="gateway", thread_id=f"gateway:{target_id}",
            message_id=f"gw-user:{client_id}", meta={"source": "gateway"},
        )
        repo_conversation.append(
            user_id=user_id, target_id=target_id, content=reply,
            role="assistant", channel="gateway", thread_id=f"gateway:{target_id}",
            message_id=f"gw-assistant:{client_id}", meta={"source": "gateway"},
        )
        return json_response({
            "success": True,
            "reply": reply,
            "target_id": target_id,
        })
    except Exception as e:
        log_err(f"网关对话失败: {e}")
        return json_response({"error": "ai_call_failed", "message": str(e)}, 500)


async def handle_internal_state(request):
    """GET /internal/state：情绪 / 关系 / 书架摘要"""
    from ..core import state as cfg
    from ..life import reading as life_reading
    from ..life import relation as life_relation
    from ..life import state as life_state

    uid = _internal_uid(request)
    tid = str(cfg.MASTER_QQ) if uid == "__owner__" else uid
    st = life_state.current(tid=None if uid == "__owner__" else uid) or {}
    try:
        rel = life_relation.get(tid)
    except Exception:
        rel = 0.0
    try:
        shelf = life_reading.load(tid)
    except Exception:
        shelf = {"books": []}
    return json_response({
        "ok": True,
        "data": {
            "user_id": uid,
            "mood": st.get("mood"),
            "energy": st.get("energy"),
            "lonely": st.get("lonely"),
            "emotion": st.get("emotion", ""),
            "relation": rel,
            "reading": shelf,
        },
    })


async def handle_internal_cron(request):
    """GET /internal/cron：当前用户的定时任务"""
    from ..core import state as cfg
    from ..schedule import cron

    uid = _internal_uid(request)
    target = str(cfg.MASTER_QQ) if uid == "__owner__" else uid
    rows = []
    for task in cron.list_tasks(target):
        rows.append({
            "id": task.get("id"),
            "schedule_type": task.get("schedule_type"),
            "content": task.get("content"),
            "at_time": task.get("at_time"),
            "weekdays": task.get("weekdays"),
            "once_at": str(task.get("once_at")) if task.get("once_at") else None,
            "rule": task.get("rule"),
            "timing": task.get("timing"),
            "enabled": bool(task.get("enabled")),
            "next_ts": str(task.get("next_ts")) if task.get("next_ts") else None,
        })
    return json_response({"ok": True, "data": rows})


async def handle_internal_diary(request):
    """GET /internal/diary：最近日记"""
    from ..core import state as cfg
    from ..infra.conn import get_cursor

    uid = _internal_uid(request)
    target = str(cfg.MASTER_QQ) if uid == "__owner__" else uid
    try:
        limit = max(1, min(int(request.query.get("limit") or 20), 100))
    except ValueError:
        return json_response({"ok": False, "error": "bad limit"}, status=400)
    c = get_cursor()
    c.execute(
        "SELECT diary_date, content, created_at FROM diaries "
        "WHERE target_id=%s ORDER BY diary_date DESC LIMIT %s", (target, limit))
    rows = []
    for r in c.fetchall():
        rows.append({
            "date": str(r["diary_date"]),
            "content": r["content"] or "",
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        })
    return json_response({"ok": True, "data": rows})


async def handle_internal_shelf(request):
    """GET /internal/shelf：书架 / 阅读进度"""
    from ..core import state as cfg
    from ..life import reading as life_reading

    uid = _internal_uid(request)
    target = str(cfg.MASTER_QQ) if uid == "__owner__" else uid
    return json_response({"ok": True, "data": life_reading.load(target)})


@web.middleware
async def auth_middleware(request, handler):
    """Bearer Token 鉴权；/api/health 与 /internal/* 免鉴权（只监听本机）"""
    if request.path == "/api/health" or request.path.startswith("/internal/"):
        return await handler(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return json_response(
            {"error": "missing_auth_header", "message": "缺少 Authorization header"},
            status=401
        )
    token = auth_header[7:]
    if not hmac.compare_digest(token, apicfg.API_TOKEN):
        return json_response(
            {"error": "invalid_token", "message": "Token 无效"},
            status=403
        )
    return await handler(request)


async def start_api_server():
    """启动 HTTP API 服务器，返回 AppRunner"""
    _semaphore = asyncio.Semaphore(apicfg.MAX_CONCURRENT_REQUESTS)
    apicfg.load_api_token()

    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/usage", handle_usage)
    app.router.add_get("/api/memory", handle_memory)
    app.router.add_get("/api/logs", handle_logs)
    app.router.add_get("/api/token", handle_get_token)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/command", handle_command)
    app.router.add_get("/internal/history", handle_internal_history)
    app.router.add_post("/internal/chat", handle_internal_chat)
    app.router.add_get("/internal/state", handle_internal_state)
    app.router.add_get("/internal/cron", handle_internal_cron)
    app.router.add_get("/internal/diary", handle_internal_diary)
    app.router.add_get("/internal/shelf", handle_internal_shelf)

    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    site = web.TCPSite(runner, apicfg.API_HOST, apicfg.API_PORT, reuse_address=True, reuse_port=True)
    await site.start()

    log_system(f"API 服务器已启动: http://{apicfg.API_HOST}:{apicfg.API_PORT}")
    log_system(f"API Token: {apicfg.API_TOKEN[:12]}...")
    log_system(f"最大并发: {apicfg.MAX_CONCURRENT_REQUESTS}")

    return runner

