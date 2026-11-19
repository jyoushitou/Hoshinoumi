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
    """GET /api/conversations：owner 的 QQ 会话列表。"""
    from ..infra import repo_conversation, tenant
    uid = tenant.owner_id()
    rows = repo_conversation.threads(uid, limit=50)
    if not rows and uid != tenant.OWNER_ID:
        rows = repo_conversation.threads(tenant.OWNER_ID, limit=50)
    return json_response({"ok": True, "data": rows})


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
    uid = tenant.owner_id()
    rows = repo_conversation.recent(target, limit=limit, user_id=uid)
    if not rows and uid != tenant.OWNER_ID:
        rows = repo_conversation.recent(target, limit=limit, user_id=tenant.OWNER_ID)
    data = []
    for r in rows:
        item = dict(r)
        if item.get("created_at") is not None:
            item["created_at"] = str(item["created_at"])
        from ..infra import image_store
        image_store.attach_image(item)
        data.append(item)
    return json_response({"ok": True, "data": data})

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
