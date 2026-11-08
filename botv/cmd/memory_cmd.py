# ===================== 记忆类命令 =====================
# event / clear：查看与清除某个对象的记忆
# 迁移自 commands.py（v5-R5）

from botv.core import state as cfg
from ..config import MASTER_QQ
from ..db import get_cursor, load_events_from_db
from .registry import command


@command("event")
async def cmd_event(ctx):
    """!event [uid] - 查看事件记忆"""
    parts = ctx.parts
    target = parts[1] if len(parts) > 1 else str(MASTER_QQ)
    try:
        events = load_events_from_db(target, limit=10)
        if events:
            lines = [f"📅 {target} 的事件记忆（最近{len(events)}条）："]
            for i, (summary, tags) in enumerate(events, 1):
                tag_str = f" [{tags}]" if tags else ""
                lines.append(f"  {i}. {summary}{tag_str}")
            return "\n".join(lines)
        return f"📅 {target} 暂无事件记忆"
    except Exception as e:
        return f"❌ 查询事件失败: {e}"


@command("clear")
async def cmd_clear(ctx):
    """!clear [uid] - 清除对话记忆与事件"""
    parts = ctx.parts
    target = parts[1] if len(parts) > 1 else str(MASTER_QQ)
    try:
        c = get_cursor()
        c.execute("DELETE FROM user_memory WHERE target_id=%s", (target,))
        c.execute("DELETE FROM events WHERE target_id=%s", (target,))
        c.connection.commit()
        if target in cfg.user_memory_pool:
            del cfg.user_memory_pool[target]
        return f"已清除 {target} 的对话记忆和事件记录"
    except Exception as e:
        return f"清除失败: {e}"


@command("profile")
async def cmd_profile(ctx):
    """!profile [uid] 查看画像；!profile set <uid> <字段> <值> 写入"""
    from ..infra.repo_profile import format_profile, set_profile

    parts = ctx.parts
    if len(parts) >= 5 and parts[1].lower() == "set":
        target, field, value = parts[2], parts[3], " ".join(parts[4:])
        ok = set_profile(target, field, value)
        return f"✅ 已记录：{target} {field}={value}" if ok else "用法: !profile set <uid> <字段> <值>"
    if len(parts) >= 4 and parts[1].lower() == "set":
        return "用法: !profile set <uid> <字段> <值>"
    target = parts[1] if len(parts) > 1 else str(MASTER_QQ)
    return format_profile(target)
