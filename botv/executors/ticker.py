# ===================== 30 秒心跳（v17.3 U3） =====================
# 原来 runner 里有个 `while True: ... await sleep(1)` 的循环，每秒醒一次。
# 现在改成调度器上的一个事件：每 30 秒投递一次 `minute_tick`。
#
# 搬过来的活儿：
#   - 跨天初始化（清触发记录、算当天任务时刻）
#   - 凌晨 3 点写昨天的日记
#   - 生日检查
#   - 代码模式超时退出
#   - 定时场景派发（投递 schedule_scene 事件）
#   - 日程/待办检查（投递 agenda_remind / pending_nudge 事件）
#
# 仍然保留的：所有「重活」都以事件形式投递，tick 本身只判断。

import asyncio
import time
from datetime import timedelta

from ..config import CST, MASTER_QQ
from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_err, log_system

TICK_INTERVAL = 30          # 秒
_TIMEOUT = 15               # tick 自身的超时（重活都投递出去了，不该久留）

_state = {
    "day": None,
    "workday": True,
    "last_due": 0.0,
    "tick_handle": None,
    "count": 0,
    "last_watch": 0.0,
    "backup_month": "",
}


def _now():
    from datetime import datetime

    return datetime.now(CST)


async def _run_backup_bg():
    try:
        from ..infra.backup import run_backup
        from ..infra.blocking import run_blocking
        return await run_blocking(run_backup, name="backup")
    except Exception as e:
        log_err(f"[备份] 自动备份失败: {e}")
        return None


@register("minute_tick", priority=Priority.EVENT, timeout=_TIMEOUT,
          description="每 30 秒的心跳：跨天、日记、生日、场景派发、日程检查")
async def handle_minute_tick(ev):
    from ..schedule import runner as R

    now = _now()
    today = now.date()
    cur_minute = now.hour * 60 + now.minute
    _state["count"] += 1

    # ---------- 跨天初始化 ----------
    if today != _state["day"]:
        workday = R.is_workday_today()
        cfg.daily_trigger.clear()
        cfg.triggered_today.clear()
        cfg.today = today
        _state["day"] = today
        _state["workday"] = workday
        log_system(f"[心跳] 跨天 {today}：{'工作日' if workday else '休息日'}")

    # ---------- v18.19：每月 1 号 04:30 自动备份 ----------
    month_key = now.strftime("%Y-%m")
    if (now.day == 1 and now.hour == 4 and now.minute == 30
            and _state["backup_month"] != month_key):
        _state["backup_month"] = month_key
        try:
            import asyncio as _aio
            _aio.create_task(_run_backup_bg())
            log_system("[备份] 本月自动备份已投递")
        except Exception as e:
            log_err(f"[备份] 投递失败: {e}")

    # ---------- 凌晨 3 点写昨天日记 ----------
    if now.hour == 3 and now.minute == 0:
        prev_date = today - timedelta(days=1)
        key = f"diary_{prev_date}"
        if key not in cfg.daily_trigger:
            cfg.daily_trigger.add(key)
            log_system(f"[心跳] 投递写日记 {prev_date}")
            try:
                from .diary import submit as submit_diary
                submit_diary(prev_date.isoformat())
            except Exception as e:
                log_err(f"[心跳] 日记投递失败: {e}")

    # ---------- 04:00 定时任务对账 ----------
    if now.hour == 4 and now.minute == 0:
        key = f"cron_sync_{today}"
        if key not in cfg.daily_trigger:
            cfg.daily_trigger.add(key)
            try:
                from ..schedule import cron as cron_mod
                n = cron_mod.schedule_all()
                log_system(f"[定时] 04:00 对账：重建 {n} 个钩子")
            except Exception as e:
                log_err(f"[定时] 对账失败: {e}")

    # ---------- v19.1：04:00 清理短期对话（1 天 / 100 条） ----------
    if now.hour == 4 and now.minute == 0:
        key = f"conversation_cleanup_{today}"
        if key not in cfg.daily_trigger:
            cfg.daily_trigger.add(key)
            try:
                from ..infra import repo_conversation
                n = repo_conversation.cleanup()
                log_system(f"[对话] 04:00 清理 {n} 条")
            except Exception as e:
                log_err(f"[对话] 清理失败: {e}")

    # ---------- 生日 ----------
    await _maybe_birthday(now, today)

    # ---------- 代码模式超时 ----------
    if cfg.CODE_MODE and cfg.CODE_MODE_LAST_MSG_TIME > 0:
        if time.time() - cfg.CODE_MODE_LAST_MSG_TIME > cfg.CODE_MODE_TIMEOUT:
            cfg.CODE_MODE = False
            cfg.CODE_MODE_LAST_MSG_TIME = 0
            log_system("[心跳] 代码模式超时退出")

    # v17.7：定时场景改由 cron_tasks 的钩子驱动（scripts/seed_scenes.py 导入）
    # 这里不再轮询 SCHEDULE_TASKS，避免和 cron 钩子重复触发。

    # v18.7：日程/待办已改成 call_at 秒级钩子（schedule/items.py），tick 不再扫 due
    # 每 60 秒做一次钩子看门狗（不补发，只重排丢失的）
    if time.time() - _state["last_watch"] > 60:
        _state["last_watch"] = time.time()
        try:
            from ..schedule import cron as cron_mod
            n = cron_mod.watchdog()
            if n:
                log_err(f"[定时] 看门狗重排 {n} 条")
        except Exception as e:
            log_err(f"[定时] 看门狗失败: {e}")
        try:
            from ..schedule import items as item_hooks
            item_hooks.watchdog()
        except Exception as e:
            log_err(f"[日程] 看门狗失败: {e}")

    return {"ok": True, "count": _state["count"]}


async def _maybe_birthday(now, today):
    """两个生日（主人 9/6、奈绪 11/13）"""
    from ..schedule import runner as R

    checks = [
        (f"birthday_{today.year}", 9, 6, 12, _owner_birthday),
        (f"nao_birthday_{today.year}", 11, 13, 8, _nao_birthday),
    ]
    for key, month, day, hour, fn in checks:
        if key in cfg.daily_trigger:
            continue
        if (now.month, now.day, now.hour, now.minute) != (month, day, hour, 0):
            continue
        cfg.daily_trigger.add(key)
        try:
            await fn(now)
        except Exception as e:
            log_err(f"[心跳] 生日失败({key}): {e}")


async def _owner_birthday(now):
    from ..ai.client import get_character_reply
    from ..ai.parse import parse_ai_reply
    from ..chat.send import make_image_msg, send_private_msg, send_short_reply
    from ..image import fetch_and_save_acg_image, get_best_image
    from ..infra.repo_memory import add_target_memory

    age = now.year - 2006
    rep = await get_character_reply(f"生日快乐,今年{age}岁了", str(MASTER_QQ))
    dialog, action, img_kw, event, refined_kw = parse_ai_reply(rep)
    add_target_memory(str(MASTER_QQ), f"今天是我{age}岁生日", rep, img_kw,
                      refined_kw, event or f"主人过{age}岁生日")
    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
    fp = await get_best_image(["生日快乐", "生日", "蛋糕", "庆祝", "happy"], str(MASTER_QQ))
    msg = make_image_msg(fp)
    if msg:
        await send_private_msg(MASTER_QQ, msg, cfg.active_ws_qq)
    log_system(f"主人生日快乐！今年 {age} 岁")


async def _nao_birthday(now):
    import random

    from ..ai.client import get_character_reply
    from ..ai.parse import parse_ai_reply
    from ..chat.send import make_image_msg, send_private_msg, send_short_reply
    from ..image import fetch_and_save_acg_image, search_local_image_by_tags
    from ..infra.repo_memory import add_target_memory

    rep = await get_character_reply("奈绪生日快乐", str(MASTER_QQ))
    dialog, action, img_kw, event, refined_kw = parse_ai_reply(rep)
    add_target_memory(str(MASTER_QQ), "友利奈绪生日", rep, img_kw, refined_kw,
                      event or "今天是我(奈绪)的生日")
    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
    results = search_local_image_by_tags(["奈绪", "友利奈绪", "Charlotte", "夏洛特"], limit=5)
    if results:
        fp = random.choice(results)[2]
        msg = make_image_msg(fp)
        if msg:
            await send_private_msg(MASTER_QQ, msg, cfg.active_ws_qq)
    else:
        fp = await fetch_and_save_acg_image()
        msg = make_image_msg(fp)
        if msg:
            await send_private_msg(MASTER_QQ, msg, cfg.active_ws_qq)
    log_system("奈绪生日快乐！")


# ---------- 自我重排 ----------

def schedule_tick(loop=None, delay=None, scheduler=None):
    from ..scheduler.dispatcher import get_scheduler

    loop = loop or asyncio.get_event_loop()
    sched = scheduler or get_scheduler()
    delay = TICK_INTERVAL if delay is None else delay

    def _fire():
        try:
            sched.submit("minute_tick", "tick:minute")
        finally:
            schedule_tick(loop, delay, sched)

    _state["tick_handle"] = loop.call_later(delay, _fire)
    return _state["tick_handle"]


def cancel_tick():
    h = _state.get("tick_handle")
    if h is not None:
        try:
            h.cancel()
        except Exception:
            pass
        _state["tick_handle"] = None


def stats():
    return {"count": _state["count"], "day": str(_state["day"]),
            "interval": TICK_INTERVAL}
