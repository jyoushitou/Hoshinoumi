# ===================== 日记执行器（v17.3） =====================
# 写日记要调模型，可能几十秒——不能塞在 30 秒心跳里（心跳 15 秒就超时了）。
#
#   minute_tick（15 秒）→ 判断「该写日记了」→ 投递 diary_write
#   diary_write（300 秒）→ 真正生成 + 存库
#
# 一天一次，key 带日期，天然去重。

from ..config import MASTER_QQ
from ..events.base import Priority
from ..events.registry import register
from ..log import log_err, log_system


@register("diary_write", priority=Priority.EVENT, timeout=300, retries=1,
          description="生成某一天的日记并落库")
async def handle_diary_write(ev):
    """ev.args = (日期字符串 'YYYY-MM-DD',)"""
    from ..schedule import runner as R

    args = getattr(ev, "args", ()) or ()
    day = args[0] if args else ""
    if not day:
        return {"ok": False, "reason": "没有日期"}

    log_system(f"[日记] 开始生成 {day}")
    try:
        text = await R.generate_diary(str(MASTER_QQ), day)
    except Exception as e:
        log_err(f"[日记] 生成失败({day}): {e}")
        return {"ok": False, "reason": "生成失败"}

    log_system(f"[日记] {day} 完成（{len(text or '')} 字）")
    return {"ok": True, "day": day, "length": len(text or "")}


def submit(day, scheduler=None):
    """投递一次写日记"""
    from ..scheduler.dispatcher import get_scheduler

    sched = scheduler or get_scheduler()
    return sched.submit("diary_write", f"diary:{day}", args=(day,))
