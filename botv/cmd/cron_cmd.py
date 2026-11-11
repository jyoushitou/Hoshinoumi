# ===================== 定时任务命令（v17.7） =====================
# 主人用命令精确控制定时消息。
#
#     !cron                              列表
#     !cron add 07:30 daily 叫我起床
#     !cron add 20:00 mon,fri 提醒我健身
#     !cron once 2026-11-15 09:00 交报告
#     !cron every 30 喝口水
#     !cron del 3
#     !cron on 3 / !cron off 3
#
# 建完立刻挂钩子，不用等 04:00 对账。

from ..core import state as cfg
from .registry import command

HELP = """⏰ 定时消息

!cron                          列出全部
!cron add HH:MM daily 内容      每天
!cron add HH:MM mon,fri 内容    每周（mon..sun）
!cron once YYYY-MM-DD HH:MM 内容  一次性
!cron every 分钟 内容           每隔几分钟
!cron del <id>                  删除
!cron on|off <id>               启用/停用"""


def _fmt_task(t):
    flag = "✅" if int(t.get("enabled") or 0) else "⏸️"
    kind = t.get("schedule_type")
    if kind == "daily":
        when = f"每天 {t.get('at_time')}"
    elif kind == "weekly":
        when = f"周{t.get('weekdays')} {t.get('at_time')}"
    elif kind == "once":
        when = f"一次性 {t.get('once_at')}"
    else:
        when = f"每 {t.get('interval_min')} 分钟"
    src = "对话" if t.get("source") == "chat" else "命令"
    return (f"{flag} #{t['id']} {when} · {t.get('content', '')[:30]}"
            f"（{src}｜下次 {t.get('next_ts') or '待排'}）")


@command("cron")
async def cmd_cron(ctx):
    """!cron - 定时消息管理"""
    from ..schedule import cron

    parts = ctx.parts[1:]
    uid = str(ctx.uid)
    sub = (parts[0].lower() if parts else "list")

    # 列表
    if sub in ("list", "") or not parts:
        try:
            tasks = cron.list_tasks(uid)
        except Exception as e:
            return f"❌ 读任务失败：{e}"
        if not tasks:
            return "⏰ 还没有定时消息\n" + HELP
        return "⏰ 定时消息：\n" + "\n".join(_fmt_task(t) for t in tasks)

    if sub == "help":
        return HELP

    try:
        if sub == "del":
            tid = int(parts[1])
            ok = cron.remove(tid)
            cron.cancel(tid)
            return f"🗑️ 已删除 #{tid}" if ok else f"❌ 删除失败 #{tid}"

        if sub in ("on", "off"):
            tid = int(parts[1])
            on = sub == "on"
            ok = cron.set_enabled(tid, on)
            if not ok:
                return f"❌ 操作失败 #{tid}"
            if on:
                task = cron.get(tid)
                if task:
                    cron.schedule_one(task)
                return f"✅ 已启用 #{tid}"
            cron.cancel(tid)
            return f"⏸️ 已停用 #{tid}"

        if sub == "add":
            return _cmd_add(uid, parts[1:])

        if sub == "once":
            return _cmd_once(uid, parts[1:])

        if sub == "every":
            return _cmd_every(uid, parts[1:])

        return "❌ 不认识的子命令\n" + HELP
    except IndexError:
        return "❌ 参数不够\n" + HELP
    except ValueError:
        return "❌ 参数格式不对（id/时间要数字）\n" + HELP


def _schedule(task_id, task):
    """建完立刻挂钩子"""
    try:
        from ..schedule import cron
        cron.schedule_one(cron.get(task_id) or task)
        return True
    except Exception:
        return False


def _cmd_add(uid, args):
    """add HH:MM daily|mon,fri 内容"""
    from ..schedule import cron

    if len(args) < 3:
        return "❌ 用法：!cron add 07:30 daily 叫我起床"
    at_time = args[0]
    when = args[1].lower()
    content = " ".join(args[2:]).strip()
    if not _valid_time(at_time):
        return "❌ 时间格式：HH:MM（如 07:30）"

    if when == "daily":
        tid = cron.add(uid, "daily", content, at_time=at_time, source="command")
    else:
        days = when.replace("周", "").replace("星期", "")
        # 支持「一,三,五」→ 1,3,5
        cn = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
              "六": "6", "日": "7", "天": "7"}
        days = ",".join(cn.get(d, d) for d in days.replace("，", ",").split(","))
        tid = cron.add(uid, "weekly", content, at_time=at_time,
                       weekdays=days, source="command")

    if not tid:
        return "❌ 写入失败"
    task = cron.get(tid)
    _schedule(tid, task)
    return f"✅ 建好了 #{tid}\n{_fmt_task(task)}" if task else f"✅ 建好了 #{tid}"


def _cmd_once(uid, args):
    """once YYYY-MM-DD HH:MM 内容"""
    from ..schedule import cron

    if len(args) < 3:
        return "❌ 用法：!cron once 2026-11-15 09:00 交报告"
    day, hm = args[0], args[1]
    content = " ".join(args[2:]).strip()
    if not _valid_date(day):
        return "❌ 日期格式：YYYY-MM-DD"
    if not _valid_time(hm):
        return "❌ 时间格式：HH:MM"

    tid = cron.add(uid, "once", content,
                   once_at=f"{day} {hm}:00", source="command")
    if not tid:
        return "❌ 写入失败"
    task = cron.get(tid)
    _schedule(tid, task)
    return f"✅ 建好了 #{tid}\n{_fmt_task(task)}" if task else f"✅ 建好了 #{tid}"


def _cmd_every(uid, args):
    """every 分钟 内容"""
    from ..schedule import cron

    if len(args) < 2:
        return "❌ 用法：!cron every 30 喝口水"
    try:
        minutes = int(args[0])
    except ValueError:
        return "❌ 分钟要整数"
    if minutes < 5:
        return "❌ 最少 5 分钟（太频繁会烦人）"
    content = " ".join(args[1:]).strip()
    tid = cron.add(uid, "interval", content, interval_min=minutes, source="command")
    if not tid:
        return "❌ 写入失败"
    task = cron.get(tid)
    _schedule(tid, task)
    return f"✅ 建好了 #{tid}\n{_fmt_task(task)}" if task else f"✅ 建好了 #{tid}"


def _valid_time(s):
    if ":" not in s:
        return False
    try:
        h, m = s.split(":")[0], s.split(":")[1]
        return 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except (ValueError, IndexError):
        return False


def _valid_date(s):
    from datetime import datetime

    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False
