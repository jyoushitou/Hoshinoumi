# ===================== 空闲读书执行器（v17.1.0） =====================
# 把「空闲时读一章」从 runner 里搬出来，变成注册到调度器上的事件。
#
# 流程：
#   idle_tick 事件（每 30 分钟自我重排，P2）
#        ↓ 闸门：深夜 / 刚聊过 / 今天读够了
#   idle_read 事件（P2，key=read:<tid>:<book>）
#        ↓ worker 执行
#   抓目录 → 抓正文（可能 OCR）→ 摘要 → 落库
#
# 为什么拆两级：tick 只做判断（毫秒级），read 才是重活（几十秒）。

import asyncio
import time

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_system

TICK_INTERVAL = 1800        # 30 分钟
_tick_handle = None
_last_run = {}


def _now():
    return time.time()


def _tid(ev):
    """从事件里取 target_id；没传就用主人"""
    args = getattr(ev, "args", ()) or ()
    return str(args[0]) if args else str(cfg.MASTER_QQ)


@register("idle_tick", priority=Priority.IDLE, timeout=30,
          description="每 30 分钟判断要不要读书")
async def handle_idle_tick(ev):
    """只做判断：该不该读书；该就投递 idle_read"""
    from ..life import reading as life_reading
    from ..scheduler.dispatcher import get_scheduler

    ok, why = life_reading.should_read(getattr(cfg, "last_user_msg_ts", 0.0))
    if not ok:
        log_api(f"[空闲] 不读：{why}")
        return {"ok": False, "reason": why}

    tid = _tid(ev)
    data = life_reading.load(tid)
    book = life_reading.current_book(data)
    sched = get_scheduler()

    if not book:
        sched.submit("idle_pick_book", f"pick:{tid}", args=(tid,))
        return {"ok": True, "reason": "去挑书"}

    sched.submit("idle_read", f"read:{tid}:{book.get('url', '')}", args=(tid,))
    return {"ok": True, "reason": "投递读书"}


@register("idle_pick_book", priority=Priority.IDLE, timeout=120,
          description="从热榜挑一本开始追")
async def handle_pick_book(ev):
    from ..life import novel as life_novel
    from ..life import reading as life_reading

    tid = _tid(ev)
    book, msg = await life_reading.pick_from_rank(
        tid, life_novel.fetch_rank, life_novel.fetch_book)
    if book:
        log_system(f"[空闲] 开始追书：{book.get('title', '')}")
    return {"ok": bool(book), "msg": msg}


@register("idle_read", priority=Priority.IDLE, timeout=300, retries=1,
          description="读一章并生成摘要")
async def handle_read(ev):
    from ..life import novel as life_novel
    from ..life import reading as life_reading

    tid = _tid(ev)

    if _now() - _last_run.get(tid, 0) < 60:
        log_api("[空闲] 刚读过，跳过")
        return {"ok": False, "reason": "刚读过"}

    out = await life_reading.read_once(
        tid, life_novel.fetch_book, life_novel.fetch_chapter,
        life_reading.summarize_chapter)
    _last_run[tid] = _now()
    if out.get("ok"):
        log_system(f"[空闲] 读书完成：{out.get('chapter')}")
    else:
        log_api(f"[空闲] 没读成：{out.get('reason')}")
    return out


# ---------- tick 的自我重排 ----------

def schedule_tick(loop=None, delay=None, scheduler=None):
    """安排下一次 tick；每次触发后再排下一次"""
    from ..scheduler.dispatcher import get_scheduler

    loop = loop or asyncio.get_event_loop()
    sched = scheduler or get_scheduler()
    delay = TICK_INTERVAL if delay is None else delay

    def _fire():
        try:
            sched.submit("idle_tick", "idle:tick")
        finally:
            schedule_tick(loop, delay, sched)

    global _tick_handle
    _tick_handle = loop.call_later(delay, _fire)
    return _tick_handle


def cancel_tick():
    global _tick_handle
    if _tick_handle is not None:
        try:
            _tick_handle.cancel()
        except Exception:
            pass
        _tick_handle = None
