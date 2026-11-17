# ===================== !plan 学习计划（v34.0.1） =====================

from .registry import command


@command("plan", "查看学习计划（today/week/import/export）")
async def cmd_plan(ctx):
    from ..life import study_plan as sp
    from ..core import state as cfg

    uid = str(ctx.uid)
    parts = ctx.args
    sub = (parts[0].lower() if parts else "week")
    if sub in ("today", "今天"):
        import datetime
        week = sp.monday_of(datetime.date.today()).isoformat()
        plan = sp.load_week(uid, week)
        day = sp.DAYS[datetime.date.today().weekday()]
        return sp.format_day(plan, day)
    if sub in ("done", "skip"):
        if len(parts) < 3:
            return "用法：!plan done|skip <day> <no>"
        import datetime
        day = parts[1].lower()
        no = int(parts[2])
        week = sp.monday_of(datetime.date.today()).isoformat()
        c = sp.set_status(uid, week, day, no, "done" if sub == "done" else "skipped")
        return "✅ 已更新" if c else "❌ 没找到这条任务"

    if sub == "move":
        if len(parts) < 4:
            return "用法：!plan move <day> <no> <to_day> [to_no]"
        import datetime
        week = sp.monday_of(datetime.date.today()).isoformat()
        c = sp.move_item(uid, week, parts[1], int(parts[2]), parts[3],
                         int(parts[4]) if len(parts) > 4 else None)
        return "↪️ 已顺延" if c else "❌ 没找到这条任务"

    if sub in ("week", "list", ""):
        import datetime
        week = sp.monday_of(datetime.date.today()).isoformat()
        return sp.format_week(sp.load_week(uid, week))
    if sub in ("show", "week"):
        return sp.format_week(sp.load_week(uid, parts[1] if len(parts) > 1 else ""))
    return "用法：!plan [today|week]"
