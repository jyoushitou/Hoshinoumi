# ===================== 对话类路由 =====================
# POST /api/chat、POST /api/command
# 迁移自 api_server.py（v5-R5），逻辑逐字未改

from bot.core import state as cfg
from ..ai.client import get_character_reply
from ..cmd import formatters as fmt
from ..infra.repo_ai import get_recent_usage
from ..log import log_err
from .common import json_response, format_dt


def _clean_api_segments(text: str) -> list[str]:
    """把模型原始五行输出拆成用户可见气泡，剥离内部元数据。"""
    import re
    from ..chat.reply import split_reply_text
    dialog, action, _meta = split_reply_text(str(text or ""))
    lines = list(dialog) + ([action] if action else [])
    out = []
    for line in lines:
        line = re.sub(r"^【[^】]{1,12}】\s*", "", str(line)).strip()
        if line:
            out.append(line)
    return out[:4] or ["……"]


def _clean_api_reply(text: str) -> str:
    return "\n".join(_clean_api_segments(text))


async def handle_chat(request):
    """POST /api/chat - AI对话（和QQ完全一致，共享记忆）"""
    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "invalid_json", "message": "请求体必须是 JSON 格式"}, 400)

    message = body.get("message", "").strip()
    if not message:
        return json_response({"error": "empty_message", "message": "message 不能为空"}, 400)

    target_id = str(body.get("target_id", "")).strip()
    if not target_id:
        return json_response({"error": "missing_target_id", "message": "target_id 不能为空，用于记忆隔离"}, 400)

    keywords = body.get("keywords", None)

    try:
        reply = await get_character_reply(message, target_id, keywords)
        segments = _clean_api_segments(reply)
        clean = "\n".join(segments)
        try:
            from ..infra import repo_conversation, tenant
            uid = tenant.owner_id()
            thread = f"web:private:{target_id}"
            repo_conversation.append(user_id=uid, target_id=target_id, content=message,
                                     role="user", channel="web", thread_id=thread)
            for segment in segments:
                repo_conversation.append(user_id=uid, target_id=target_id, content=segment,
                                         role="assistant", channel="web", thread_id=thread)
        except Exception as _e:
            log_err(f"Web 对话落库失败: {_e}")
        return json_response({
            "success": True,
            "reply": clean,
            "segments": segments,
            "target_id": target_id,
        })
    except Exception as e:
        log_err(f"API 对话调用失败: {e}")
        return json_response({"error": "ai_call_failed", "message": str(e)}, 500)


async def handle_command(request):
    """POST /api/command - 执行真实命令注册表中的只读/文本命令。"""
    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "invalid_json", "message": "请求体必须是 JSON 格式"}, 400)

    raw = str(body.get("command", "") or "").strip().lstrip("!")
    args = body.get("args", []) or []
    if not raw:
        return json_response({"error": "empty_command", "message": "command 不能为空"}, 400)
    cmd = raw.lower()
    if not isinstance(args, list):
        return json_response({"error": "bad_args", "message": "args 必须是数组"}, 400)

    # 发送类/进程控制类命令不能从 Web API 执行
    blocked = {"say", "sayg", "img", "acg", "voice", "sticker", "exit", "quit", "reload", "backup", "update", "adduser", "set", "code"}
    if cmd in blocked:
        return json_response({"error": "command_not_allowed", "message": f"!{cmd} 不能在 Web API 执行"}, 403)

    try:
        from ..cmd import registry
        from ..cmd.registry import CommandContext
        # 导入命令模块，触发 @command 注册
        from ..cmd import admin, basic, books_cmd, cron_cmd, diary_cmd, history_cmd
        from ..cmd import memory_cmd, ops, plan_cmd, plugin_cmd, presence_cmd, query, route_cmd, gw_cmd  # noqa: F401
        if cmd not in registry.COMMANDS:
            return json_response({"error": "unknown_command", "message": f"未知命令: {cmd}"}, 400)
        from ..infra import tenant
        ctx = CommandContext(parts=[cmd, *[str(a) for a in args]], uid=tenant.owner_id(),
                             ws=None, is_group=False, gid=0)
        result = await registry.run(cmd, ctx)
        text = str(result or "")
        if cmd == "vision" and "视觉 ❌" in text:
            return json_response({"success": False, "error": "vision_failed", "command": cmd, "result": text}, 502)
        return json_response({"success": True, "command": cmd, "args": args, "result": text})
    except Exception as e:
        log_err(f"API 命令执行失败 !{cmd}: {e}")
        return json_response({"error": "command_failed", "message": str(e)}, 500)


async def handle_conversations(request):
    """GET /api/conversations：好友/群目录 + 历史聚合（含未读）。"""
    from . import qq_directory
    from ..infra import read_state, repo_conversation, repo_groups, tenant
    uid = tenant.owner_id()
    rows = repo_conversation.threads(uid, limit=100)
    if not rows and uid != tenant.OWNER_ID:
        rows = repo_conversation.threads(tenant.OWNER_ID, limit=100)
    merged = {str(r["target_id"]): dict(r) for r in rows}
    for r in merged.values():
        r.setdefault("type", "unknown")
        r.setdefault("name", r["target_id"])
        r.setdefault("member_count", 0)
    try:
        directory = await qq_directory.directory()
    except Exception:
        directory = {"groups": [], "friends": []}
    for item in directory.get("groups", []):
        row = merged.get(item["target_id"]) or {
            "target_id": item["target_id"], "count": 0,
            "last_message": "", "last_role": "", "updated_at": "",
        }
        row.update(item)
        merged[item["target_id"]] = row
    for item in directory.get("friends", []):
        if item["target_id"] in merged:
            merged[item["target_id"]].update(item)
    try:
        for item in repo_groups.list_for(uid):
            row = merged.get(item["id"]) or {"target_id": item["id"], "count": 0, "last_message": "", "last_role": "", "updated_at": item.get("created_at") or ""}
            row.update({"type": "group", "name": item["name"], "member_count": item["member_count"], "custom": True})
            merged[item["id"]] = row
    except Exception:
        pass
    for row in merged.values():
        row["last_read_id"] = read_state.last_read(uid, row["target_id"])
        row["unread"] = read_state.unread_count(uid, row["target_id"])
    owner = str(tenant.owner_id())
    if owner not in merged:
        merged[owner] = {
            "target_id": owner, "type": "private", "name": "奈绪",
            "member_count": 0, "count": 0, "last_message": "",
            "last_role": "", "updated_at": "",
        }
    out = sorted(merged.values(), key=lambda x: str(x.get("updated_at") or ""), reverse=True)[:100]
    return json_response({"ok": True, "data": out})



async def handle_topic(request):
    """POST /api/topic：判断当前话题是否结束，给出追问建议（规则版）。"""
    import time
    from ..infra import repo_conversation, repo_meta, tenant
    try:
        body = await request.json()
    except Exception:
        body = {}
    target = str((body or {}).get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    uid = tenant.owner_id()
    key = f"topic_check:{uid}:{target}"
    try:
        last_ts = float(repo_meta.get_value(key, "0") or 0)
    except (TypeError, ValueError):
        last_ts = 0
    if time.time() - last_ts < 30:
        return json_response({"ok": False, "error": "rate_limited", "retry_after": 30 - int(time.time() - last_ts)}, status=429)
    repo_meta.set_value(key, str(time.time()))
    rows = repo_conversation.recent(target, limit=8, user_id=uid)
    texts = [str(r.get("content") or "").strip() for r in rows if str(r.get("role")) == "user"]
    last = texts[-1] if texts else ""
    endings = ("晚安", "拜拜", "先这样", "去忙了", "睡了", "回头聊", "先不聊了", "好的", "嗯")
    closed = bool(last) and any(last.endswith(x) for x in endings)
    followup = "刚刚说到哪儿了？要接着聊吗？" if closed else "这个话题你还有什么想补充的吗？"
    return json_response({
        "ok": True, "target_id": target, "status": "closed" if closed else "open",
        "reason": "last_message_ending" if closed else "no_closing_signal",
        "followup": followup,
    })


async def handle_recall(request):
    """POST /api/messages/{id}/recall：2 分钟内撤回自己的消息。"""
    import json
    from datetime import datetime
    from ..infra import repo_conversation, tenant

    message_id = (request.match_info.get("id") if getattr(request, "match_info", None) else None)
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if not message_id:
        message_id = (body or {}).get("message_id")
    try:
        message_id = int(message_id)
    except (TypeError, ValueError):
        return json_response({"ok": False, "error": "bad_message_id"}, status=400)
    uid = tenant.owner_id()
    row = repo_conversation.get_by_id(message_id, user_id=uid)
    if not row and uid != tenant.OWNER_ID:
        row = repo_conversation.get_by_id(message_id, user_id=tenant.OWNER_ID)
    if not row:
        return json_response({"ok": False, "error": "message_not_found"}, status=404)
    if str(row.get("role") or "") != "user":
        return json_response({"ok": False, "error": "not_own_message"}, status=403)
    try:
        created = datetime.strptime(str(row.get("created_at"))[:19], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - created).total_seconds() > 120:
            return json_response({"ok": False, "error": "recall_window_expired"}, status=403)
    except ValueError:
        pass
    try:
        meta = json.loads(row.get("meta") or "{}") if isinstance(row.get("meta"), str) else (row.get("meta") or {})
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta["recalled"] = True
    meta["recalled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repo_conversation.set_meta(message_id, row.get("user_id") or uid, meta)
    return json_response({"ok": True, "message_id": message_id, "target_id": row.get("target_id"), "recalled": True})


async def handle_read_state(request):
    """GET /api/read-state?target_id=：最后已读位点。"""
    from ..infra import read_state, tenant
    target = (request.query.get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    uid = tenant.owner_id()
    last = read_state.last_read(uid, target)
    return json_response({"ok": True, "target_id": target, "last_read_id": last, "unread": read_state.unread_count(uid, target)})


async def handle_read(request):
    """POST /api/read：上报已读位点。"""
    from ..infra import read_state, tenant
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, status=400)
    target = str((body or {}).get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    try:
        last = int((body or {}).get("last_read_id") or 0)
    except (TypeError, ValueError):
        return json_response({"ok": False, "error": "bad_last_read_id"}, status=400)
    uid = tenant.owner_id()
    value = read_state.mark_read(uid, target, last)
    return json_response({"ok": True, "target_id": target, "last_read_id": value, "unread": read_state.unread_count(uid, target)})


# v35.7.23：命令目录从注册表动态生成，客户端不硬编码
_OWNER_COMMANDS = {
    "reload", "set", "exit", "quit", "clear", "say", "sayg",
    "backup", "plugin", "adduser", "gw", "config", "code", "apikeys",
}


async def handle_commands(request):
    """GET /api/commands：命令目录元数据。"""
    from ..cmd import registry
    from ..cmd import formatters

    rows = []
    for cmd in sorted(registry.COMMANDS.values(), key=lambda c: c.name):
        rows.append({
            "name": "!" + cmd.name,
            "group": formatters._cmd_group(cmd.name),
            "help": formatters._cmd_desc(cmd),
            "owner": cmd.name in _OWNER_COMMANDS,
            "usage": None,
            "args": [],
            "subcommands": [],
        })
    return json_response({"ok": True, "count": len(rows), "data": rows})


async def handle_history(request):
    """GET /api/history?target_id=...：owner 的会话历史。"""
    from ..infra import repo_conversation, tenant
    target = (request.query.get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    try:
        limit = int(request.query.get("limit") or 100)
    except ValueError:
        limit = 100
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        rows = repo_conversation.recent(target, limit=limit, user_id=tenant.owner_id(), cursor=c)
    finally:
        try: c.close()
        except Exception: pass
    data = []
    for r in rows:
        item = dict(r)
        if item.get("created_at") is not None:
            item["created_at"] = str(item["created_at"])
        data.append(item)
    return json_response({"ok": True, "data": data})
