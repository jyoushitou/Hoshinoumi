# ===================== 对话类路由 =====================
# POST /api/chat、POST /api/command
# 迁移自 api_server.py（v5-R5），逻辑逐字未改

from bot.core import state as cfg
from ..ai.client import get_character_reply
from ..cmd import formatters as fmt
from ..infra.repo_ai import get_recent_usage
from ..log import log_err
from .common import json_response, format_dt


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
        return json_response({
            "success": True,
            "reply": reply,
            "target_id": target_id,
        })
    except Exception as e:
        log_err(f"API 对话调用失败: {e}")
        return json_response({"error": "ai_call_failed", "message": str(e)}, 500)


async def handle_command(request):
    """POST /api/command - 执行只读类命令"""
    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "invalid_json", "message": "请求体必须是 JSON 格式"}, 400)

    cmd = body.get("command", "").strip().lower()
    args = body.get("args", [])

    try:
        if cmd == "help":
            result = fmt.build_cmd_help()
        elif cmd == "status":
            result = fmt.format_status_detailed()
        elif cmd == "task":
            result = "⏰ `!task` 已移除：真实计划用 `!cron`，钩子状态用 `!hooks`"
        elif cmd == "memory":
            if args:
                target = args[0]
                if target in cfg.user_memory_pool:
                    deq = cfg.user_memory_pool[target]
                    lines = [f"{target} 的对话记忆（共{len(deq)}条）："]
                    for i, (u, b) in enumerate(deq[-10:], 1):
                        lines.append(f"  {i}. 用户: {u[:30]}...")
                        lines.append(f"     奈绪: {b[:30]}...")
                    result = "\n".join(lines)
                else:
                    result = f"{target} 暂无对话记忆"
            else:
                result = fmt.format_memory_stats()
        elif cmd == "sticker":
            result = fmt.format_sticker_stats()
        elif cmd == "clip":
            result = fmt.format_clip_status()
        elif cmd == "keywords":
            result = fmt.format_keywords()
        elif cmd == "apikeys":
            result = fmt.format_apikeys()
        elif cmd == "usage":
            records = get_recent_usage(10)
            if not records:
                result = "暂无token用量记录"
            else:
                lines = ["最近10次AI调用token用量："]
                total_prompt = 0
                total_completion = 0
                total_all = 0
                for i, r in enumerate(records, 1):
                    model = r["model_name"]
                    pt = r["prompt_tokens"] or 0
                    ct = r["completion_tokens"] or 0
                    tt = r["total_tokens"] or 0
                    tm = format_dt(r.get("created_at"))
                    lines.append(f"  {i}. [{model}] 输入{pt}+输出{ct}={tt} ({tm})")
                    total_prompt += pt
                    total_completion += ct
                    total_all += tt
                lines.append("  ---")
                lines.append(f"  合计: 输入{total_prompt}+输出{total_completion}={total_all}")
                result = "\n".join(lines)
        else:
            return json_response({"error": "unknown_command", "message": f"未知命令: {cmd}"}, 400)

        return json_response({
            "success": True,
            "command": cmd,
            "args": args,
            "result": result,
        })
    except Exception as e:
        return json_response({"error": "command_failed", "message": str(e)}, 500)

async def handle_conversations(request):
    """GET /api/conversations：好友/群目录 + 历史聚合（含未读）。"""
    from . import qq_directory
    from ..infra import read_state, repo_conversation, tenant
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
    for row in merged.values():
        row["last_read_id"] = read_state.last_read(uid, row["target_id"])
        row["unread"] = read_state.unread_count(uid, row["target_id"])
    out = sorted(merged.values(), key=lambda x: str(x.get("updated_at") or ""), reverse=True)[:100]
    return json_response({"ok": True, "data": out})



async def handle_topic(request):
    """POST /api/topic：判断当前话题是否结束，给出追问建议（规则版）。"""
    from ..infra import repo_conversation, tenant
    try:
        body = await request.json()
    except Exception:
        body = {}
    target = str((body or {}).get("target_id") or "").strip()
    if not target:
        return json_response({"ok": False, "error": "target_id required"}, status=400)
    uid = tenant.owner_id()
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
