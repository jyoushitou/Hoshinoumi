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
    if sub in ("week", "list", ""):
        import datetime
        week = sp.monday_of(datetime.date.today()).isoformat()
        return sp.format_week(sp.load_week(uid, week))
    if sub in ("show", "week"):
        return sp.format_week(sp.load_week(uid, parts[1] if len(parts) > 1 else ""))
    return "用法：!plan [today|week]"
