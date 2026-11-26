# ===================== HTTP 服务器装配 =====================
# 鉴权中间件 + 路由注册 + 启动
# 迁移自 api_server.py（v5-R5）

import asyncio
import hmac
import os

from aiohttp import web

from ..log import log_system
from . import config as apicfg
from .common import json_response
from .routes_meta import (
    handle_health, handle_healthz, handle_readyz, handle_status, handle_usage,
    handle_memory, handle_logs, handle_get_token,
)
from .routes_chat import handle_chat, handle_command, handle_conversations, handle_history, handle_commands, handle_read, handle_read_state, handle_recall, handle_topic
from .routes_persona import handle_persona, handle_export as handle_persona_export, handle_import as handle_persona_import, handle_activate as handle_persona_activate
from .routes_files import handle_files, handle_init as handle_file_init, handle_chunk as handle_file_chunk, handle_complete as handle_file_complete, handle_download as handle_file_download, handle_delete as handle_file_delete, handle_share_create as handle_file_share_create, handle_share_info as handle_file_share_info, handle_share_download as handle_file_share_download, handle_upload_status as handle_file_upload_status
from .routes_books import handle_books, handle_book, handle_book_content, handle_book_progress_get, handle_book_progress_put, handle_books_refresh
from .routes_savings import handle_savings, handle_savings_import, handle_savings_add, handle_savings_events, handle_snapshots_get, handle_snapshot_create, handle_reconcile, handle_overview, handle_monthly, handle_goals, handle_frozen, handle_fixed, handle_funds, handle_finance_audit, handle_savings_init_get, handle_savings_init_post, handle_fixed_add, handle_fixed_settle, handle_fund_buy, handle_fund_redeem
from .routes_weekly_plan import handle_weekly_get, handle_weekly_put, handle_weekly_import, handle_weekly_weeks
from .routes_reminders import handle_pending as handle_reminders_pending, handle_ack as handle_reminder_ack
from .routes_balance import handle_balance
from .routes_health import handle_summary as handle_health_summary, handle_add_meal as handle_health_add_meal, handle_delete_meal as handle_health_delete_meal, handle_recognize as handle_health_recognize, handle_init_get as handle_health_init_get, handle_init_post as handle_health_init_post, handle_add_exercise as handle_health_add_exercise, handle_delete_exercise as handle_health_delete_exercise
from .routes_memory import handle_item_update as handle_memory_item_update, handle_item_delete as handle_memory_item_delete
from .routes_groups import handle_list as handle_groups_list, handle_create as handle_groups_create
from .routes_push import handle_devices as handle_push_devices, handle_register as handle_push_register, handle_delete as handle_push_delete, handle_preferences as handle_push_preferences, handle_test as handle_push_test, handle_outbox as handle_push_outbox
from .routes_plugins import handle_list as handle_plugins_list, handle_install as handle_plugins_install, handle_toggle as handle_plugins_toggle, handle_approve as handle_plugins_approve, handle_reject as handle_plugins_reject
from .routes_cron import handle_list as handle_cron_list, handle_create as handle_cron_create, handle_update as handle_cron_update, handle_delete as handle_cron_delete, handle_run as handle_cron_run
from .routes_relation import handle_relation
from .routes_plan import handle_get as handle_plan_get, handle_put as handle_plan_put, handle_import as handle_plan_import, handle_export as handle_plan_export
from .routes_presence import handle_get as handle_presence_get, handle_post as handle_presence_post, handle_delete as handle_presence_delete
from .routes_tools import handle_list as handle_tools_list, handle_call as handle_tool_call
from .routes_endpoints import (
    handle_list as handle_endpoints_list,
    handle_register as handle_endpoint_register,
    handle_disable as handle_endpoint_disable,
    handle_messages as handle_endpoint_messages,
    handle_ack as handle_endpoint_ack,
)


async def handle_internal_history(request):
    """v19.2 / v35.5.6：本机内部历史接口，支持 after_seq 增量。"""
    from ..infra import repo_conversation

    target = (request.query.get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    try:
        limit = int(request.query.get("limit") or 100)
        before = int(request.query["before"]) if request.query.get("before") else None
        after_seq = int(request.query["after_seq"]) if request.query.get("after_seq") not in (None, "") else None
    except ValueError:
        return json_response({"ok": False, "error": "bad limit/before/after_seq"}, status=400)
    owner = (request.headers.get("X-User-Id")
             or request.headers.get("X-Owner-Id")
             or request.query.get("user_id") or "__owner__")
    if owner == "owner":
        owner = "__owner__"
    if after_seq is not None:
        rows = repo_conversation.after(target, after_id=after_seq, limit=limit, user_id=owner)
    else:
        rows = repo_conversation.recent(target, limit=limit, before_id=before, user_id=owner)
    data = []
    from ..infra import image_store
    for r in rows:
        item = dict(r)
        if item.get("created_at") is not None:
            item["created_at"] = str(item["created_at"])
        image_store.attach_image(item)
        data.append(item)
    seqs = [int(x["id"]) for x in data if str(x.get("id", "")).isdigit()]
    next_seq = max(seqs) if seqs else (after_seq or 0)
    return json_response({"ok": True, "data": data, "next_seq": next_seq, "has_more": len(data) >= limit})


def _internal_uid(request):
    """v23：网关注入 X-User-Id；兼容旧 X-Owner-Id / 本机 query。"""
    return (request.headers.get("X-User-Id")
            or request.headers.get("X-Owner-Id")
            or request.query.get("user_id")
            or "__owner__").strip()


async def handle_internal_chat(request):
    """POST /internal/chat：网关转发 + 写入网关对话历史（v21.2）"""
    import base64
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
    image = str(body.get("image") or "").strip()
    sticker = str(body.get("sticker") or "").strip()
    audio = str(body.get("audio") or "").strip()
    if not target_id:
        return json_response({"error": "missing_target_id", "message": "target_id 不能为空"}, 400)
    if not message and not image and not sticker and not audio:
        return json_response({"error": "empty_message", "message": "message/附件不能同时为空"}, 400)
    if sum(bool(x) for x in (image, sticker, audio)) > 1:
        return json_response({"error": "too_many_attachments", "message": "一次只能发一个附件"}, 400)

    base_text = message
    user_text = base_text or "[图片]" if image else base_text or "[表情包]" if sticker else base_text or "[语音]" if audio else base_text or "[附件]"
    kind = "image" if image else "sticker" if sticker else "voice" if audio else ""
    attachment_path = ""
    attachment_desc = ""
    attachment_bytes = b""
    attachment_mime = ""
    attachment_src = sticker or image or audio

    if attachment_src:
        attachment_mime = "image/png" if kind != "voice" else "audio/webm"
        try:
            if attachment_src.startswith("data:") and "," in attachment_src:
                head, raw = attachment_src.split(",", 1)
                attachment_mime = head[5:].split(";", 1)[0] or attachment_mime
            else:
                raw = attachment_src
            attachment_bytes = base64.b64decode(raw, validate=True)
        except Exception:
            return json_response({"error": "attachment_invalid", "message": "附件数据无法解码"}, 400)
        if not attachment_bytes or len(attachment_bytes) > 4 * 1024 * 1024:
            return json_response({"error": "attachment_too_large", "message": "附件不能超过 4MB"}, 413)

        if kind == "image":
            try:
                from ..ai.vision import describe_image
                desc, _tags = await describe_image(attachment_bytes)
            except Exception as e:
                log_err(f"图片识别失败: {e}")
                desc = None
            if not desc:
                return json_response({"error": "image_vision_failed", "message": "图片识别失败，未发送"}, 502)
            attachment_desc = str(desc)[:200]
            message = f"{base_text}\n[用户发来一张图片：{attachment_desc}]" if base_text else f"[用户发来一张图片：{attachment_desc}]"
        elif kind == "sticker":
            message = f"{base_text}\n[用户发来一个表情包]" if base_text else "[用户发来一个表情包]"
        else:
            transcript = ""
            try:
                from ..speech import asr
                transcript = await asr.transcribe(attachment_bytes, "voice.webm") or ""
            except Exception as e:
                log_err(f"语音识别失败: {e}")
            attachment_desc = str(transcript)[:300]
            message = f"{base_text}\n[用户发来一段语音{'，转写：' + transcript if transcript else '，未识别出文字'}]" if base_text else f"[用户发来一段语音{'，转写：' + transcript if transcript else '，未识别出文字'}]"

    # 同一轮成功后再落盘，避免 AI 失败留下孤儿附件
    if attachment_bytes:
        from ..infra import image_store
        attachment_path = image_store.save(attachment_bytes, attachment_mime)
        if not attachment_path:
            return json_response({"error": "attachment_save_failed", "message": "附件保存失败"}, 500)

    user_id = _internal_uid(request)
    # v21 单用户：JWT sub=owner，但历史/QQ 统一存 __owner__
    if user_id == "owner":
        user_id = "__owner__"
    client_id = str(body.get("client_message_id") or uuid.uuid4().hex)
    try:
        reply = await get_character_reply(message, target_id, body.get("keywords"))
        if not isinstance(reply, str) or not reply.strip():
            return json_response({"error": "empty_reply", "message": "AI 返回空回复"}, 500)

        # 只写成功的一轮；user/assistant 各自稳定 id，重试不会重复
        repo_conversation.append(
            user_id=user_id, target_id=target_id, content=user_text,
            role="user", channel="gateway", thread_id=f"gateway:{target_id}",
            message_id=f"gw-user:{client_id}", meta={"source": "gateway", "kind": kind, "attachment_path": attachment_path, "attachment_desc": attachment_desc},
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


async def handle_internal_auth_verify(request):
    """POST /internal/auth/verify：网关登录用户（只返回 user_id/role）"""
    from ..infra import repo_users

    try:
        body = await request.json()
        uid = str(body.get("user_id") or "").strip()
        password = str(body.get("password") or "")
        setup_code = str(body.get("setup_code") or "")
        row, err = repo_users.verify_login(uid, password, setup_code)
        if err:
            code = 403 if err in ("password_setup_required", "banned") else 401
            return json_response({"ok": False, "error": err}, code)
        return json_response({"ok": True, "data": {"user_id": row["id"], "role": row["role"]}})
    except Exception as e:
        return json_response({"ok": False, "error": "auth_failed", "message": str(e)}, 500)


async def handle_internal_auth_owner(request):
    """GET /internal/auth/owner：网关 owner secret 登录时取真实 owner user_id"""
    from ..infra import tenant
    return json_response({"ok": True, "data": {
        "user_id": tenant.owner_id(), "role": "owner"}})


async def handle_internal_auth_register(request):
    """POST /internal/auth/register：邀请码注册"""
    from ..infra import repo_users, tenant

    try:
        body = await request.json()
        invite = str(body.get("invite") or "").strip()
        uid = str(body.get("user_id") or "").strip()
        password = str(body.get("password") or "")
        nickname = str(body.get("nickname") or uid)
        if not invite or not uid or len(password) < 8:
            return json_response({"ok": False, "error": "invalid_input"}, 400)
        role = repo_users.consume_invite(invite, uid)
        if not role:
            return json_response({"ok": False, "error": "invalid_invite"}, 403)
        row = repo_users.create_with_password(uid, password, nickname, role)
        return json_response({"ok": True, "data": {"user_id": row["id"], "role": row["role"]}})
    except Exception as e:
        return json_response({"ok": False, "error": "register_failed", "message": str(e)}, 500)


async def handle_internal_audit(request):
    """POST /internal/audit：网关审计落库（只存元数据，不存 body/token）"""
    from ..infra.conn import get_cursor
    from ..log import log_err

    try:
        body = await request.json()
        c = get_cursor()
        c.execute(
            "INSERT INTO gateway_log(owner,path,status,cost_ms,ip,request_id) "
            "VALUES(%s,%s,%s,%s,%s,%s)",
            (str(body.get("owner") or "")[:64],
             str(body.get("path") or "")[:255],
             int(body.get("status") or 0),
             int(body.get("cost_ms") or 0),
             str(body.get("ip") or "")[:64],
             str(body.get("request_id") or "")[:64]),
        )
        c.connection.commit()
        return json_response({"ok": True})
    except Exception as e:
        log_err(f"网关审计写入失败: {e}")
        return json_response({"ok": False, "error": "audit_failed"}, 500)


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
        rel = life_relation.get(tid, user_id=uid)
    except Exception:
        rel = 0.0
    try:
        shelf = life_reading.load(tid, user_id=uid)
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
    for task in cron.list_tasks(target, user_id=uid):
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
        "WHERE user_id=%s AND target_id=%s ORDER BY diary_date DESC LIMIT %s",
        (uid, target, limit))
    rows = []
    for r in c.fetchall():
        rows.append({
            "date": str(r["diary_date"]),
            "content": r["content"] or "",
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        })
    return json_response({"ok": True, "data": rows})


async def handle_internal_shelf(request):
    """GET /internal/shelf：书架 / 阅读进度（v35.9.26.0 正式契约）"""
    from ..core import state as cfg
    from ..life import reading as life_reading

    uid = _internal_uid(request)
    target = str(cfg.MASTER_QQ) if uid == "__owner__" else uid
    data = life_reading.load(target, user_id=uid)
    books = []
    for book in data.get("books") or []:
        if not isinstance(book, dict):
            continue
        title = str(book.get("title") or "").strip()
        if not title:
            continue
        books.append({
            "title": title,
            "url": str(book.get("url") or ""),
            "last_no": int(book.get("last_no") or 0),
            "last_title": str(book.get("last_title") or ""),
            "intro": str(book.get("intro") or ""),
        })
    active = books[0] if books else None
    return json_response({
        "ok": True,
        "data": {
            "books": books,
            "book_count": len(books),
            "active_book": active,
            "day": str(data.get("day") or ""),
            "chapters": int(data.get("chapters") or 0),
            "daily_chapters": int(life_reading.DAILY_CHAPTERS),
            "quota_left": int(life_reading.quota_left(data)),
        },
    })


@web.middleware
async def auth_middleware(request, handler):
    """Bearer Token 鉴权；/healthz、/readyz、/api/health、/internal/* 免鉴权（只监听本机）"""
    if request.path in ("/api/health", "/healthz", "/readyz", "/api/avatar") or request.path.startswith("/internal/") or request.path.startswith("/api/files/share/"):
        return await handler(request)
    # endpoint 用自己的 token 拉消息/ack；注册/列表/停用仍走 owner Bearer
    if request.path.startswith("/api/endpoints/") and (
            request.path.endswith("/messages") or request.path.endswith("/ack")):
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


async def handle_avatar(request):
    """GET /api/avatar?type=qq&id=10001：后端头像缓存，前端不直连 qlogo。"""
    from ..infra import avatar_store
    kind = (request.query.get("type") or "qq").lower()
    if kind not in ("qq", "group"):
        kind = "qq"
    ident = (request.query.get("id") or "").strip()
    if not ident:
        raise web.HTTPBadRequest(text="missing id")
    body, ctype = await asyncio.to_thread(avatar_store.resolve, kind, ident)
    if not body:
        raise web.HTTPNotFound(text="avatar unavailable")
    return web.Response(body=body, content_type=ctype, headers={
        "Cache-Control": "public, max-age=86400",
        "X-Avatar-Cache": "hoshinoumi",
    })


async def start_api_server():
    """启动 HTTP API 服务器，返回 AppRunner"""
    _semaphore = asyncio.Semaphore(apicfg.MAX_CONCURRENT_REQUESTS)
    apicfg.load_api_token()

    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/healthz", handle_healthz)
    app.router.add_get("/readyz", handle_readyz)
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/avatar", handle_avatar)
    app.router.add_get("/api/usage", handle_usage)
    app.router.add_get("/api/memory", handle_memory)
    app.router.add_patch("/api/memory/items/{id}", handle_memory_item_update)
    app.router.add_delete("/api/memory/items/{id}", handle_memory_item_delete)
    app.router.add_get("/api/logs", handle_logs)
    app.router.add_get("/api/token", handle_get_token)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/command", handle_command)
    app.router.add_get("/api/conversations", handle_conversations)
    app.router.add_get("/api/history", handle_history)
    app.router.add_get("/api/read-state", handle_read_state)
    app.router.add_post("/api/read", handle_read)
    app.router.add_post("/api/messages/{id}/recall", handle_recall)
    app.router.add_post("/api/topic", handle_topic)
    app.router.add_get("/api/commands", handle_commands)
    app.router.add_get("/api/groups", handle_groups_list)
    app.router.add_post("/api/groups", handle_groups_create)
    app.router.add_get("/api/endpoints", handle_endpoints_list)
    app.router.add_post("/api/endpoints", handle_endpoint_register)
    app.router.add_delete("/api/endpoints/{id}", handle_endpoint_disable)
    app.router.add_get("/api/endpoints/{id}/messages", handle_endpoint_messages)
    app.router.add_post("/api/endpoints/{id}/ack", handle_endpoint_ack)
    app.router.add_get("/api/tools", handle_tools_list)
    app.router.add_post("/api/tools/{name}/call", handle_tool_call)
    app.router.add_get("/api/persona", handle_persona)
    app.router.add_get("/api/savings", handle_savings)
    app.router.add_post("/api/savings/entries", handle_savings_add)
    app.router.add_get("/api/savings/init", handle_savings_init_get)
    app.router.add_post("/api/savings/init", handle_savings_init_post)
    app.router.add_get("/api/savings/overview", handle_overview)
    app.router.add_get("/api/savings/goals", handle_goals)
    app.router.add_get("/api/savings/frozen", handle_frozen)
    app.router.add_get("/api/savings/fixed", handle_fixed)
    app.router.add_post("/api/savings/fixed", handle_fixed_add)
    app.router.add_post("/api/savings/fixed/{id}/settle", handle_fixed_settle)
    app.router.add_get("/api/savings/funds", handle_funds)
    app.router.add_post("/api/savings/funds/buy", handle_fund_buy)
    app.router.add_post("/api/savings/funds/{id}/redeem", handle_fund_redeem)
    app.router.add_get("/api/savings/monthly", handle_monthly)
    app.router.add_get("/api/finance/audit", handle_finance_audit)
    app.router.add_get("/api/savings/snapshots", handle_snapshots_get)
    app.router.add_post("/api/savings/snapshots", handle_snapshot_create)
    app.router.add_get("/api/savings/reconcile", handle_reconcile)
    app.router.add_get("/api/savings/events", handle_savings_events)
    app.router.add_get("/api/balance", handle_balance)
    app.router.add_get("/api/health/init", handle_health_init_get)
    app.router.add_post("/api/health/init", handle_health_init_post)
    app.router.add_get("/api/health/summary", handle_health_summary)
    app.router.add_get("/api/push/devices", handle_push_devices)
    app.router.add_post("/api/push/devices", handle_push_register)
    app.router.add_delete("/api/push/devices/{id}", handle_push_delete)
    app.router.add_get("/api/push/preferences", handle_push_preferences)
    app.router.add_patch("/api/push/preferences", handle_push_preferences)
    app.router.add_post("/api/push/test", handle_push_test)
    app.router.add_get("/api/push/outbox", handle_push_outbox)
    app.router.add_get("/api/plugins", handle_plugins_list)
    app.router.add_post("/api/plugins/install", handle_plugins_install)
    app.router.add_post("/api/plugins/{id}/toggle", handle_plugins_toggle)
    app.router.add_post("/api/plugins/{id}/approve", handle_plugins_approve)
    app.router.add_post("/api/plugins/{id}/reject", handle_plugins_reject)
    app.router.add_post("/api/health/meals", handle_health_add_meal)
    app.router.add_delete("/api/health/meals/{id}", handle_health_delete_meal)
    app.router.add_post("/api/health/exercises", handle_health_add_exercise)
    app.router.add_delete("/api/health/exercises/{id}", handle_health_delete_exercise)
    app.router.add_post("/api/health/recognize", handle_health_recognize)
    app.router.add_get("/api/relation", handle_relation)
    app.router.add_get("/api/weekly-plan/weeks", handle_weekly_weeks)
    app.router.add_get("/api/weekly-plan", handle_weekly_get)
    app.router.add_post("/api/weekly-plan", handle_weekly_put)
    app.router.add_post("/api/weekly-plan/import", handle_weekly_import)
    app.router.add_post("/api/savings/import", handle_savings_import)
    app.router.add_get("/api/persona/export", handle_persona_export)
    app.router.add_post("/api/persona/import", handle_persona_import)
    app.router.add_post("/api/persona/activate", handle_persona_activate)
    app.router.add_get("/api/plan", handle_plan_get)
    app.router.add_post("/api/plan", handle_plan_put)
    app.router.add_post("/api/plan/import", handle_plan_import)
    app.router.add_get("/api/plan/export", handle_plan_export)
    app.router.add_get("/api/presence", handle_presence_get)
    app.router.add_get("/internal/presence", handle_presence_get)
    app.router.add_post("/internal/presence", handle_presence_post)
    app.router.add_delete("/internal/presence", handle_presence_delete)
    app.router.add_get("/internal/history", handle_internal_history)
    app.router.add_post("/internal/read", handle_read)
    app.router.add_post("/internal/recall", handle_recall)
    app.router.add_post("/internal/topic", handle_topic)
    app.router.add_post("/internal/chat", handle_internal_chat)
    app.router.add_post("/internal/audit", handle_internal_audit)
    app.router.add_post("/internal/auth/verify", handle_internal_auth_verify)
    app.router.add_get("/internal/auth/owner", handle_internal_auth_owner)
    app.router.add_post("/internal/auth/register", handle_internal_auth_register)
    app.router.add_get("/api/state", handle_internal_state)
    app.router.add_get("/internal/state", handle_internal_state)
    app.router.add_get("/api/reminders", handle_reminders_pending)
    app.router.add_post("/api/reminders/{id}/ack", handle_reminder_ack)
    app.router.add_get("/api/cron", handle_cron_list)
    app.router.add_post("/api/cron", handle_cron_create)
    app.router.add_patch("/api/cron/{id}", handle_cron_update)
    app.router.add_delete("/api/cron/{id}", handle_cron_delete)
    app.router.add_post("/api/cron/{id}/run", handle_cron_run)
    app.router.add_get("/internal/cron", handle_internal_cron)
    app.router.add_get("/internal/diary", handle_internal_diary)
    app.router.add_get("/api/files", handle_files)
    app.router.add_post("/api/files/init", handle_file_init)
    app.router.add_get("/api/files/{id}/upload", handle_file_upload_status)
    app.router.add_put("/api/files/{id}/chunk", handle_file_chunk)
    app.router.add_post("/api/files/{id}/complete", handle_file_complete)
    app.router.add_get("/api/files/{id}/download", handle_file_download)
    app.router.add_delete("/api/files/{id}", handle_file_delete)
    app.router.add_post("/api/files/{id}/share", handle_file_share_create)
    app.router.add_get("/api/files/share/{token}", handle_file_share_info)
    app.router.add_get("/api/files/share/{token}/download", handle_file_share_download)
    app.router.add_get("/api/books", handle_books)
    app.router.add_post("/api/books/refresh", handle_books_refresh)
    app.router.add_get("/api/books/{id}", handle_book)
    app.router.add_get("/api/books/{id}/content", handle_book_content)
    app.router.add_get("/api/books/{id}/progress", handle_book_progress_get)
    app.router.add_put("/api/books/{id}/progress", handle_book_progress_put)
    app.router.add_get("/internal/shelf", handle_internal_shelf)

    async def _avatar_ctx(_app):
        from ..infra import avatar_store
        task = asyncio.create_task(avatar_store.loop_daily())
        try:
            yield
        finally:
            task.cancel()
    app.cleanup_ctx.append(_avatar_ctx)

    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    from ..core import worker
    if os.getenv("NAO_INTERNAL_TCP", "1") != "0":
        if os.name == "nt":
            # Windows 无 AF_UNIX 支持时，内部 API 走 loopback TCP；27004 仍由帧服务占用
            internal_port = int(os.getenv("NAO_INTERNAL_API_PORT", "27007"))
            site = web.TCPSite(runner, "127.0.0.1", internal_port)
            await site.start()
            log_system(f"内部 API 已启动: http://127.0.0.1:{internal_port}（27004 由 TCP 帧服务占用）")
        else:
            sock = worker.internal_api_socket()
            try:
                import os as _os
                if _os.path.exists(sock):
                    _os.unlink(sock)
            except OSError:
                pass
            site = web.UnixSite(runner, sock)
            await site.start()
            worker.chmod_socket(sock)
            log_system(f"内部 API 已启动: unix:{sock}（27004 由 TCP 帧服务占用）")
    elif worker.enabled():
        sock = worker.prepare_socket("api.sock")
        site = web.UnixSite(runner, sock)
        await site.start()
        worker.chmod_socket(sock)
        log_system(f"API worker 已启动: unix:{sock}")
    else:
        site = web.TCPSite(runner, apicfg.API_HOST, apicfg.API_PORT, reuse_address=True, reuse_port=True)
        await site.start()
        log_system(f"API 服务器已启动: http://{apicfg.API_HOST}:{apicfg.API_PORT}")
    log_system(f"API Token: {apicfg.API_TOKEN[:12]}...")
    log_system(f"最大并发: {apicfg.MAX_CONCURRENT_REQUESTS}")

    return runner

