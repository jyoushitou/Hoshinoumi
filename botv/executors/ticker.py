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
from ..schedule.config import SCHEDULE_TASKS
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
}


def _now():
    from datetime import datetime

    return datetime.now(CST)


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
        cfg.task_trigger_minute.clear()
        cfg.today = today
        cfg.task_trigger_minute.update(R.calc_day_tasks(today, workday))
        _state["day"] = today
        _state["workday"] = workday
        log_system(f"[心跳] 跨天 {today}：{'工作日' if workday else '休息日'}，"
                   f"{len(cfg.task_trigger_minute)} 个任务点")

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

    # ---------- 生日 ----------
    await _maybe_birthday(now, today)

    # ---------- 代码模式超时 ----------
    if cfg.CODE_MODE and cfg.CODE_MODE_LAST_MSG_TIME > 0:
        if time.time() - cfg.CODE_MODE_LAST_MSG_TIME > cfg.CODE_MODE_TIMEOUT:
            cfg.CODE_MODE = False
            cfg.CODE_MODE_LAST_MSG_TIME = 0
            log_system("[心跳] 代码模式超时退出")

    # ---------- 定时场景派发 ----------
    for task in SCHEDULE_TASKS:
        key = f"{task['scene']}_{today}"
        if key in cfg.daily_trigger:
            continue
        if today.weekday() not in task["weekday"]:
            continue
        if task.get("only_holiday") and _state["workday"]:
            continue
        if cfg.task_trigger_minute.get(key) != cur_minute:
            continue
        cfg.daily_trigger.add(key)
        log_system(f"[心跳] 派发场景：{task['scene']}")
        try:
            from .schedule import submit_scene
            submit_scene(task["scene"], today)
        except Exception as e:
            log_err(f"[心跳] 场景派发失败: {e}")

    # ---------- 日程/待办（每 30 秒一次） ----------
    if time.time() - _state["last_due"] > 30:
        _state["last_due"] = time.time()
        try:
            await R.process_due(now)
        except Exception as e:
            log_err(f"[心跳] 日程检查失败: {e}")

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
