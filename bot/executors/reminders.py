# ===================== 日程 / 待办执行器（v17.1.0） =====================
# process_due 里的「生成 + 发送」搬出来，变成两个事件：
#
#   agenda_remind（P1，key=agenda:<id>）   日程到点提醒
#   pending_nudge（P1，key=pending:<id>）  待办到点回访
#
# 判定（到点没有、闸门放不放行）仍留在 runner 的 process_due 里——
# 它只做「查一遍列表」，毫秒级；真正要调模型的部分投给 worker。

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_err


@register("agenda_remind", priority=Priority.EVENT, timeout=90, retries=1,
          description="日程到点提醒")
async def handle_agenda(ev):
    """ev.args = (日程文本, 日程 id)"""
    from ..ai.client import get_character_reply
    from ..chat.send import send_short_reply
    from ..life.agenda import mark_reminded as agenda_mark

    args = getattr(ev, "args", ()) or ()
    text = args[0] if args else ""
    item_id = args[1] if len(args) > 1 else None

    try:
        rep = await get_character_reply(
            f"（提醒他：{text}。一句话，别说教。）", str(cfg.MASTER_QQ))
    except Exception as e:
        log_err(f"[日程] 生成失败: {e}")
        return {"ok": False, "reason": "生成失败"}

    if not rep:
        return {"ok": False, "reason": "空回复"}

    await send_short_reply(cfg.MASTER_QQ, rep, cfg.active_ws_qq, cfg.MASTER_QQ)
    try:
        from ..life.impulse import note_proactive
        note_proactive()
    except Exception:
        pass
    if item_id is not None:
        try:
            agenda_mark(item_id)
        except Exception:
            pass
    log_api(f"[日程] 已提醒: {str(text)[:20]}")
    return {"ok": True}


@register("pending_nudge", priority=Priority.EVENT, timeout=90, retries=1,
          description="待办到点回访（承诺/时间锚点）")
async def handle_pending(ev):
    """ev.args = (描述文本, 待办 id)"""
    from ..ai.client import get_character_reply
    from ..chat.send import send_short_reply
    from ..life.pending import finish as finish_pending

    args = getattr(ev, "args", ()) or ()
    desc = args[0] if args else ""
    item_id = args[1] if len(args) > 1 else None

    try:
        rep = await get_character_reply(
            f"（{desc}。就一句话，别解释。）", str(cfg.MASTER_QQ))
    except Exception as e:
        log_err(f"[待办] 生成失败: {e}")
        return {"ok": False, "reason": "生成失败"}

    if not rep:
        return {"ok": False, "reason": "空回复"}

    await send_short_reply(cfg.MASTER_QQ, rep, cfg.active_ws_qq, cfg.MASTER_QQ)
    try:
        from ..life.impulse import note_proactive
        note_proactive()
    except Exception:
        pass
    if item_id is not None:
        try:
            finish_pending(item_id)
        except Exception:
            pass
    log_api(f"[待办] 已回访: {str(desc)[:20]}")
    return {"ok": True}


def submit_agenda(text, item_id, scheduler=None):
    from ..scheduler.dispatcher import get_scheduler

    sched = scheduler or get_scheduler()
    return sched.submit("agenda_remind", f"agenda:{item_id}", args=(text, item_id))


def submit_pending(desc, item_id, scheduler=None):
    from ..scheduler.dispatcher import get_scheduler

    sched = scheduler or get_scheduler()
    return sched.submit("pending_nudge", f"pending:{item_id}", args=(desc, item_id))
