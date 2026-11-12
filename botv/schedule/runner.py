# ===================== 定时任务主循环 =====================
# 跨天初始化、生日、自动日记、代码模式超时、任务触发、主动闲聊
# 迁移自 schedule.py（v5-R5），逻辑逐字未改

import asyncio
import random
import time as _time
from datetime import datetime, timedelta

from ..config import MASTER_QQ, CST
from botv.core import state as cfg
from ..log import log_system, log_err, log_api
from ..ai.client import get_character_reply
from ..core.types import Fallback  # v16：判断兜底文案
from ..memory import add_target_memory
from ..chat.send import send_short_reply, send_private_msg
from ..image import fetch_and_save_acg_image, search_local_image_by_tags, get_best_image
from ..utils import make_image_msg
from ..ai.parse import parse_ai_reply
from ..diary import generate_diary
from ..infra.repo_memory import load_events_from_db, load_today_life, load_old_events
from ..life.impulse import should_reach_out, note_proactive  # v10-U9
from ..life.pending import due as pending_due, finish as finish_pending, describe as describe_pending  # v10-U9b
from ..life.agenda import due_soon as agenda_due_soon, mark_reminded as agenda_mark  # v10-U10
from .config import SCHEDULE_TASKS, is_workday_today
from .planner import calc_day_tasks

# 每天首次运行的延迟（秒），用于跨天精确触发
_FIRST_RUN_DELAY = 10


class _SkipChat(Exception):
    """这次不主动发（内部信号，不打印任何东西）"""


async def process_due(now):
    """处理到点的日程与待办，返回到点发出去几条

    v10.3：从主循环里抽出来，便于用假数据做代码级测试。
    """
    sent = 0

    # v17.1：只判定「到点没有 + 闸门放不放行」，生成交给调度器
    from ..executors import reminders as reminder_exec

    # 日程提醒（v10-U10）
    try:
        for it in agenda_due_soon(60):
            ok, _why = should_reach_out(now=now, require_lonely=False)
            if not ok:
                continue
            if reminder_exec.submit_agenda(it.get("t", ""), it["id"]):
                sent += 1
                log_system(f"日程已投递: {it.get('t', '')[:20]}")
    except Exception as a_e:
        log_err(f"日程投递异常:{a_e}")

    # 待办到点：回访承诺 / 时间锚点（v10-U9b）
    try:
        for item_id, item in pending_due(now):
            ok, why = should_reach_out(now=now, require_lonely=False)
            if not ok:
                log_api(f"待办暂缓({why}): {item.get('t')}")
                continue
            if reminder_exec.submit_pending(describe_pending(item), item_id):
                sent += 1
                log_system(f"待办已投递: {item.get('t')}")
    except Exception as p_e:
        log_err(f"待办投递异常:{p_e}")

    return sent


async def cycle_task_run():
    await asyncio.sleep(_FIRST_RUN_DELAY)

    # v17.1：启动事件调度器，并把「空闲读书」交给它（每 30 分钟自己排下一次）
    try:
        from ..scheduler.dispatcher import get_scheduler
        from ..executors import idle as idle_exec
        from ..executors import proactive as proactive_exec
        _sched = get_scheduler()
        _sched.start()
        idle_exec.schedule_tick()
        proactive_exec.schedule_tick()
        try:  # v18.7：日程/待办也走秒级钩子
            from . import items as item_hooks
            n = item_hooks.schedule_all()
            log_system(f"[日程] 钩子已重建：{n} 条")
        except Exception as _e:
            log_err(f"[日程] 钩子重建失败: {_e}")
        log_system("[调度] 调度器已启动：空闲读书 + 主动消息由 tick 驱动")
    except Exception as _e:
        log_err(f"[调度] 启动失败（回退旧路径）: {_e}")
    # v17.3 U3：不再自己跑 1 秒循环——跨天 / 日记 / 生日 / 场景 / 日程
    # 全部交给调度器的 minute_tick（每 30 秒），这里只保活。
    try:
        from ..executors import cron as cron_exec  # noqa: F401  注册 cron_task
        from ..schedule import cron as cron_mod
        n = cron_mod.schedule_all()
        log_system(f"[定时] 启动对账：挂了 {n} 个钩子")
    except Exception as _e:
        log_err(f"[定时] 启动对账失败: {_e}")

    try:
        from ..executors import ticker as ticker_exec
        ticker_exec.schedule_tick()
        log_system("[调度] minute_tick 已安排（每 30 秒）")
    except Exception as _e:
        log_err(f"[调度] minute_tick 安排失败: {_e}")

    # v17.8：启动池监护线程（一个线程看线程池 + 连接池）
    try:
        from ..infra.monitor import start_monitor
        start_monitor()
    except Exception as _e:
        log_err(f"[监护] 启动失败: {_e}")

    # v17.8：不再自建保活循环——主循环 app/loop.py serve 负责常驻


# ===================== 空闲读书（v16） =====================

READ_CHECK_INTERVAL = 1800   # 30 分钟最多检查一次
_last_read_check = 0.0
