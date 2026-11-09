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

@command("todo")
async def cmd_todo(ctx):
    """!todo 看日程；!todo <文字> 添加；!todo done <id> 划掉"""
    from datetime import datetime
    from ..config import CST
    from ..life.agenda import list_all, remove, extract, add

    parts = ctx.parts
    if len(parts) >= 3 and parts[1].lower() == "done":
        return "✅ 划掉了" if remove(parts[2]) else "没找到这条"
    if len(parts) >= 2:
        text = " ".join(parts[1:])
        item = extract(text)
        if not item:
            return "没听出时间。写清楚点：!todo 周五下午三点 面试"
        add(item)
        when = datetime.fromtimestamp(item["due"], CST).strftime("%m-%d %H:%M")
        return f"✅ 记下了：{when} {item['t'][:20]}"

    items = list_all()
    if not items:
        return "📅 没有待办"
    lines = ["📅 待办："]
    for it in items[:10]:
        when = datetime.fromtimestamp(it["due"], CST).strftime("%m-%d %H:%M")
        flag = "（已提醒）" if it.get("d") else ""
        lines.append(f"  #{it['id']} {when} {it['t'][:24]}{flag}")
    return "\n".join(lines)
@command("memorybook")
async def cmd_memorybook(ctx):
    """!memorybook [uid] - 记忆本：认识多久、关系、口头禅、最近记得的事"""
    from ..config import MASTER_QQ
    from ..life import milestone, relation, habit
    from ..infra.repo_memory import load_timeline

    tid = ctx.args[0] if ctx.args else str(MASTER_QQ)
    lines = [f"📖 我和 {tid} 的记忆本"]

    try:
        lines.append(f"  认识：第 {milestone.days_together(tid)} 天")
    except Exception:
        lines.append("  认识：不知道（记不起来是哪天了）")

    try:
        aff = relation.get(tid)
        name, _desc = relation.tier_of(aff)
        lines.append(f"  关系：{name}")
    except Exception:
        pass

    try:
        phrases = habit.phrases_for(tid)
        if phrases:
            lines.append(f"  他常说的：{'、'.join(phrases)}")
    except Exception:
        pass

    try:
        rows = load_timeline(tid, days=30, limit=8)
        if rows:
            lines.append("  最近记得的事：")
            for r in rows[:8]:
                lines.append(f"    {r['day']}  {str(r['summary'])[:30]}")
        else:
            lines.append("  最近还没记住什么事")
    except Exception:
        lines.append("  记忆读取失败")

    return "\n".join(lines)