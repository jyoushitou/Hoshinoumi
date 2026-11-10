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


async def maybe_chat(now):
    """到点主动闲聊：先问她想不想说话，再决定说什么。返回是否真的发出"""
    # v10.4：每 30 分钟掷一次骰子，不再依赖预设时刻
    if now.minute % 30 != 0 or now.second > 10:
        return False
    window = now.strftime("%Y-%m-%d %H:%M")
    if window in cfg.triggered_today:
        return False
    cfg.triggered_today.add(window)  # 先标记，异常也不重复触发

    try:
        from ..life.impulse import should_chat
        has_life = False
        try:
            has_life = bool(load_today_life())
        except Exception:
            has_life = False
        ok, why, p = should_chat(now=now, has_life_event=has_life)
        if not ok:
            log_system(f"主动闲聊跳过: {why}")
            return False

        # 心情很差：只说一句，不解释
        try:
            from ..life.state import current as life_current
            mood_now = float(life_current().get("mood", 0.0))
        except Exception:
            mood_now = 0.0
        if mood_now < -0.5:
            rep = await get_character_reply(
                "（你现在心情很差，只发一句很短的话，不解释原因）", str(MASTER_QQ))
            await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
            note_proactive()
            log_system(f"主动闲聊（心情差 {mood_now:.2f}，只说一句）")
            return True

        # 分享今天的生活事件
        life_today = load_today_life()
        if life_today and random.random() < 0.5:
            seed = random.choice(life_today)
            rep = await get_character_reply(
                f"（主动找他说话。说说你今天的这件事：{seed}。别问他在不在，直接说事。）",
                str(MASTER_QQ))
            await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
            note_proactive()
            log_system(f"主动闲聊（分享生活: {seed[:20]}）")
            return True

        # v13-G46：低频惊喜——没头没尾地逗他一下
        if random.random() < 0.05:
            log_system("主动闲聊（惊喜）")
            rep = await get_character_reply(
                "（今天心情不错，突然想逗他一下：说一句没头没尾的怪话，"
                "或者突然夸他一句。别解释为什么）", str(MASTER_QQ))
            await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
            note_proactive()
            return True

        # v12-G52：有时拿一件旧事当由头，像突然想起来
        if random.random() < 0.4:
            try:
                old = load_old_events(str(MASTER_QQ), days=7, limit=3)
            except Exception:
                old = []
            if old:
                picked = random.choice(old)
                log_system(f"主动闲聊（提起旧事: {str(picked['summary'])[:20]}）")
                rep = await get_character_reply(
                    f"（你突然想起一件旧事：{picked['day']} {picked['summary']}。"
                    f"顺口提一句，别像翻旧账，也别解释为什么想起来）",
                    str(MASTER_QQ))
                await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                note_proactive()
                return True

        # 基于最近事件
        recent = load_events_from_db(str(MASTER_QQ), limit=5)
        if recent:
            chosen = random.choice(recent)[0]
            rep = await get_character_reply(f"闲聊（之前{chosen}）", str(MASTER_QQ))
            log_system(f"主动闲聊触发（基于事件: {chosen}）")
        else:
            rep = await get_character_reply("闲聊", str(MASTER_QQ))
            log_system("主动闲聊触发（无事件）")
        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
        note_proactive()
        log_system("主动闲聊触发完成")
        return True
    except Exception as e:
        log_err(f"主动闲聊执行异常:{e}")
        return False


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
        log_system("[调度] 调度器已启动：空闲读书 + 主动消息由 tick 驱动")
    except Exception as _e:
        log_err(f"[调度] 启动失败（回退旧路径）: {_e}")
    # v17.3 U3：不再自己跑 1 秒循环——跨天 / 日记 / 生日 / 场景 / 日程
    # 全部交给调度器的 minute_tick（每 30 秒），这里只保活。
    try:
        from ..executors import ticker as ticker_exec
        ticker_exec.schedule_tick()
        log_system("[调度] minute_tick 已安排（每 30 秒）")
    except Exception as _e:
        log_err(f"[调度] minute_tick 安排失败: {_e}")

    while True:
        await asyncio.sleep(3600)


# ===================== 空闲读书（v16） =====================

READ_CHECK_INTERVAL = 1800   # 30 分钟最多检查一次
_last_read_check = 0.0


async def maybe_read(now=None, force=False):
    """（v17.1 起由 executors/idle.py 接管；保留给手动触发与旧测试）

    空闲时读一章小说；返回是否真的读了

    闸门：深夜不读 / 刚聊过不读 / 今天读够了不读。
    没有在追的书 → 先从热榜挑一本。
    """
    global _last_read_check
    now = now or datetime.now(CST)
    ts = now.timestamp()

    if not force and (ts - _last_read_check) < READ_CHECK_INTERVAL:
        return False

    from ..life import novel as life_novel
    from ..life import reading as life_reading

    ok, why = life_reading.should_read(getattr(cfg, "last_user_msg_ts", 0.0), now)
    if not ok:
        return False

    data = life_reading.load(str(MASTER_QQ))
    if not life_reading.current_book(data):
        book, _msg = await life_reading.pick_from_rank(
            str(MASTER_QQ), life_novel.fetch_rank, life_novel.fetch_book)
        if not book:
            log_api("[读书] 挑书失败，跳过")
            return False
        log_system(f"开始追书：{book.get('title', '')}")

    _last_read_check = ts
    out = await life_reading.read_once(
        str(MASTER_QQ), life_novel.fetch_book, life_novel.fetch_chapter,
        life_reading.summarize_chapter, now)
    if out.get("ok"):
        log_system(f"读书完成：{out.get('chapter')}")
        await maybe_share_reading(now)  # v16-E8：攒够几个点就说一句
    else:
        log_api(f"[读书] 没读成：{out.get('reason')}")
    return bool(out.get("ok"))
async def maybe_share_reading(now=None):
    """攒够几个点就主动说一句（v16-E8）"""
    from ..life import reading as life_reading

    now = now or datetime.now(CST)
    data = life_reading.load(str(MASTER_QQ))
    if not life_reading.share_ready(data, now):
        return False

    seed = life_reading.build_share(data)
    if not seed:
        return False

    try:
        rep = await get_character_reply(
            f"（你刚看完几章，想跟他说说：{seed}。"
            f"像随口提一句，别像书评，别问他问题）", str(MASTER_QQ))
    except Exception as e:
        log_err(f"读书分享失败: {e}")
        return False
    if not rep or isinstance(rep, Fallback):
        return False

    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
    life_reading.mark_shared(data, now)
    life_reading.save(str(MASTER_QQ), data)
    log_system("读书分享已发送")
    return True


# ===================== 读书派发（v16.0.3） =====================
# 读一章可能要 30~60 秒（浏览器 + OCR + AI），绝不能 await 在主循环里。
READING_BUSY = {"task": None}


def _dispatch_reading(now=None):
    """有任务在跑就不重复派发；否则起一个后台任务"""
    t = READING_BUSY.get("task")
    if t and not t.done():
        return False
    try:
        READING_BUSY["task"] = asyncio.create_task(maybe_read(now))
        return True
    except Exception as e:
        log_err(f"读书任务派发失败: {e}")
        return False
