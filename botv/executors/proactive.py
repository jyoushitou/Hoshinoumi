# ===================== 主动消息执行器（v17.1.0） =====================
# 把 maybe_chat 里的「判断 + 生成」拆成两个事件：
#
#   proactive_tick（P1，每 30 分钟自我重排）
#        ↓ 六道闸门 + 掷骰（只判断，毫秒级）
#   proactive_say（P1，key=proactive:<tid>）
#        ↓ worker 执行（调模型、发消息，几秒）
#
# 为什么拆：tick 只是掷骰子，不该占住 worker；说的时候才需要模型。
# 去重靠 key：同一个人正在生成时，下一次 tick 不会重复投递。

import asyncio
import random
import time

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_system

TICK_INTERVAL = 1800         # 兼容旧调用
MIN_DELAY = 20 * 60          # v18.7：20–40 分钟，再随机到秒
MAX_DELAY = 40 * 60
_tick_handle = None
_ticking = {"running": False}


def _tid(ev):
    args = getattr(ev, "args", ()) or ()
    return str(args[0]) if args else str(cfg.MASTER_QQ)


@register("proactive_tick", priority=Priority.EVENT, timeout=30,
          description="每 30 分钟决定要不要主动找他")
async def handle_proactive_tick(ev):
    """只判断：该不该主动；该就投递 proactive_say"""
    from ..scheduler.dispatcher import get_scheduler

    if _ticking["running"]:
        return {"ok": False, "reason": "上一轮还没结束"}
    _ticking["running"] = True
    try:
        tid = _tid(ev)
        now = _now_dt()
        has_life = False
        try:
            from ..infra.repo_memory import load_today_life
            has_life = bool(load_today_life())
        except Exception:
            has_life = False

        from ..life.impulse import should_chat
        ok, why, p = should_chat(now=now, has_life_event=has_life)
        if not ok:
            log_api(f"[主动] 跳过：{why}")
            return {"ok": False, "reason": why, "p": p}

        queued = get_scheduler().submit("proactive_say", f"proactive:{tid}", args=(tid,))
        if queued:
            log_api(f"[主动] 通过闸门（p={p:.2f}），投递发言")
        else:
            log_api("[主动] 已有一条在飞，跳过投递")
        return {"ok": queued, "p": p, "reason": "" if queued else "已有在飞"}
    finally:
        _ticking["running"] = False


@register("proactive_say", priority=Priority.EVENT, timeout=90, retries=1,
          description="真正生成并发送主动消息")
async def handle_proactive_say(ev):
    from ..scheduler.dispatcher import get_scheduler   # noqa: F401
    from ..ai.client import get_character_reply
    from ..chat.send import send_short_reply

    tid = _tid(ev)
    seed, tag = _pick_seed()

    try:
        rep = await get_character_reply(seed, tid)
    except Exception as e:
        log_api(f"[主动] 生成失败: {e}")
        return {"ok": False, "reason": "生成失败"}

    if not rep:
        return {"ok": False, "reason": "空回复"}

    await send_short_reply(tid, rep, cfg.active_ws_qq, tid)
    try:
        from ..life.impulse import note_proactive
        note_proactive()
    except Exception:
        pass
    log_system(f"[主动] 已发送（{tag}）")
    return {"ok": True, "tag": tag}


def _pick_seed():
    """挑一个由头：心情差 / 生活分享 / 惊喜 / 旧事 / 普通"""
    # 心情很差：只说一句
    try:
        from ..life.state import current as life_current
        mood = float(life_current().get("mood", 0.0))
    except Exception:
        mood = 0.0
    if mood < -0.5:
        return ("（你现在心情很差，只发一句很短的话，不解释原因）", "心情差")

    # 分享今天的事
    try:
        from ..infra.repo_memory import load_today_life
        life_today = load_today_life() or []
    except Exception:
        life_today = []
    if life_today and random.random() < 0.5:
        seed = random.choice(life_today)
        return (f"（主动找他说话。说说你今天的这件事：{seed}。"
                f"别问他在不在，直接说事。）", f"分享生活: {str(seed)[:16]}")

    # 低频惊喜
    if random.random() < 0.05:
        return ("（今天心情不错，突然想逗他一下：说一句没头没尾的怪话，"
                "或者突然夸他一句。别解释为什么）", "惊喜")

    # 旧事重提
    if random.random() < 0.4:
        try:
            from ..infra.repo_memory import load_old_events
            old = load_old_events(str(cfg.MASTER_QQ), days=7, limit=3) or []
        except Exception:
            old = []
        if old:
            picked = random.choice(old)
            return (f"（你突然想起一件旧事：{picked.get('day', '')} "
                    f"{picked.get('summary', '')}。顺口提一句，"
                    f"别像翻旧账，也别解释为什么想起来）", "旧事")

    return ("（主动找他聊聊天。说点具体的，别问在不在）", "普通")


def _now_dt():
    from datetime import datetime

    from ..config import CST
    return datetime.now(CST)


def _now():
    return time.time()


# ---------- tick 的自我重排 ----------

def _next_delay():
    """v18.7：下次主动时间不固定在整点/半点"""
    return random.randint(MIN_DELAY, MAX_DELAY) + random.randint(0, 59)


def schedule_tick(loop=None, delay=None, scheduler=None):
    """安排下一次 proactive_tick（call_at 秒级挂载）"""
    from ..scheduler.dispatcher import get_scheduler

    loop = loop or asyncio.get_event_loop()
    sched = scheduler or get_scheduler()
    delay = _next_delay() if delay is None else delay

    def _fire():
        try:
            sched.submit("proactive_tick", "proactive:tick")
        finally:
            schedule_tick(loop, None, sched)

    global _tick_handle
    _tick_handle = loop.call_at(loop.time() + max(1.0, delay), _fire)
    return _tick_handle


def cancel_tick():
    global _tick_handle
    if _tick_handle is not None:
        try:
            _tick_handle.cancel()
        except Exception:
            pass
        _tick_handle = None
