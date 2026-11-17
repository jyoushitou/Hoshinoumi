# ===================== 学习计划提醒 tick（v34.0.3） =====================

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register


@register("plan_tick", priority=Priority.IDLE, timeout=30,
          description="学习计划到点提醒")
async def handle_plan_tick(ev):
    from ..life import study_plan
    from ..chat.send import send_short_reply
    uid = str(getattr(cfg, "MASTER_QQ", ""))
    if not uid:
        return {"ok": False}
    week, day, due = study_plan.due_items(uid)
    sent = 0
    for c in due:
        text = f"⏰ {c.get('time')} {c.get('subject','')} {c.get('task','')}".strip()
        try:
            await send_short_reply(uid, text, getattr(cfg, "active_ws_qq", None), uid, False, None)
            study_plan.mark_notified(uid, week, day, c.get("no"))
            sent += 1
        except Exception:
            pass
    return {"ok": True, "sent": sent}


def schedule_tick(loop=None, delay=60, scheduler=None):
    import asyncio
    loop = loop or asyncio.get_event_loop()
    from ..scheduler.dispatcher import get_scheduler
    sched = scheduler or get_scheduler()

    def fire():
        try:
            sched.submit("plan_tick", "plan:tick")
        finally:
            schedule_tick(loop, delay, sched)

    loop.call_later(delay, fire)
