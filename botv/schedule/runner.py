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

    # 日程提醒（v10-U10）
    try:
        for it in agenda_due_soon(60):
            ok, _why = should_reach_out(now=now, require_lonely=False)
            if not ok:
                continue
            rep = await get_character_reply(
                f"（提醒他：{it.get('t', '')}。一句话，别说教。）", str(MASTER_QQ))
            await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
            note_proactive()
            agenda_mark(it["id"])
            sent += 1
            log_system(f"日程已提醒: {it.get('t', '')[:20]}")
    except Exception as a_e:
        log_err(f"日程提醒异常:{a_e}")

    # 待办到点：回访承诺 / 时间锚点（v10-U9b）
    try:
        for item_id, item in pending_due(now):
            ok, why = should_reach_out(now=now, require_lonely=False)
            if not ok:
                log_api(f"待办暂缓({why}): {item.get('t')}")
                continue
            rep = await get_character_reply(
                f"（{describe_pending(item)}。就一句话，别解释。）", str(MASTER_QQ))
            await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
            note_proactive()
            finish_pending(item_id)
            sent += 1
            log_system(f"待办已回访: {item.get('t')}")
    except Exception as p_e:
        log_err(f"待办处理异常:{p_e}")

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
    _last_today = None  # 记录上一次检查的日期
    _is_workday = True  # 缓存当天是否工作日
    _last_due_check = 0.0  # 上次检查日程/待办的时间（节流用，函数内局部）
    while True:
        try:
            now = datetime.now(CST)
            today = now.date()
            cur_minute = now.hour * 60 + now.minute

            # ---------- 跨天/首次初始化 ----------
            if today != _last_today:
                log_system(f"定时任务：切换到 {today}")
                _is_workday = is_workday_today()
                log_system(f"今天 {'工作日' if _is_workday else '非工作日'} 催起床={'7:30' if _is_workday else '8:30'} 催睡觉=看明天工作日定")
                # 清空所有触发记录
                cfg.daily_trigger.clear()
                cfg.triggered_today.clear()
                cfg.task_trigger_minute.clear()
                cfg.today = today
                # 先计算当日所有任务触发时刻（后面闲聊要避开这些时间）
                cfg.task_trigger_minute.update(calc_day_tasks(today, _is_workday))

                # v10.4：主动闲聊不再预设时刻，改成每 30 分钟掷一次骰子
                _last_today = today
                log_system(f"定时任务初始化完成，共 {len(cfg.task_trigger_minute)} 个任务点"
                           f"（主动闲聊改为每 30 分钟掷骰）")

            # ---------- 凌晨3点自动生成昨天日记并存入数据库 ----------
            # 3点时昨天的数据已完整，AI生成日记后保存到 diaries 表（不推送）
            # 查看用 !diary <日期> 命令，从数据库读取
            if now.hour == 3 and now.minute == 0:
                prev_date = today - timedelta(days=1)
                diary_key = f"diary_{prev_date}"
                if diary_key not in cfg.daily_trigger:
                    cfg.daily_trigger.add(diary_key)  # 先标记，防重复
                    log_system(f"定时:自动写日记({prev_date})")
                    try:
                        # generate_diary 内部会保存到 diaries 表，若已存在则直接读取不重复生成
                        diary_text = await generate_diary(str(MASTER_QQ), prev_date.isoformat())
                        log_system(f"自动日记({prev_date}) 已生成并保存到数据库（{len(diary_text)}字）")
                    except Exception as diary_e:
                        log_err(f"自动日记生成失败: {diary_e}")

            # ---------- 生日检查 ----------
            birthday_flag_key = f"birthday_{today.year}"
            if (birthday_flag_key not in cfg.daily_trigger and
                    now.month == 9 and now.day == 6 and now.hour == 12 and now.minute == 0):
                age = now.year - 2006
                rep = await get_character_reply(f"生日快乐,今年{age}岁了", str(MASTER_QQ))
                dialog, action, img_kw, event, refined_kw = parse_ai_reply(rep)
                add_target_memory(str(MASTER_QQ), f"今天是我{age}岁生日", rep, img_kw, refined_kw, event or f"主人过{age}岁生日")
                await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                bd_fp = await get_best_image(["生日快乐", "生日", "蛋糕", "庆祝", "happy"], str(MASTER_QQ))
                bd_msg = make_image_msg(bd_fp)
                if bd_msg:
                    await send_private_msg(MASTER_QQ, bd_msg, cfg.active_ws_qq)
                cfg.daily_trigger.add(birthday_flag_key)
                log_system(f"主人生日快乐！今年{age}岁了")

            nao_birthday_key = f"nao_birthday_{today.year}"
            if (nao_birthday_key not in cfg.daily_trigger and
                    now.month == 11 and now.day == 13 and now.hour == 8 and now.minute == 0):
                rep = await get_character_reply("奈绪生日快乐", str(MASTER_QQ))
                dialog, action, img_kw, event, refined_kw = parse_ai_reply(rep)
                add_target_memory(str(MASTER_QQ), "友利奈绪生日", rep, img_kw, refined_kw, event or "今天是我(奈绪)的生日")
                await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                nao_results = search_local_image_by_tags(["奈绪", "友利奈绪", "Charlotte", "夏洛特"], limit=5)
                if nao_results:
                    nao_fp = random.choice(nao_results)[2]
                    nao_msg = make_image_msg(nao_fp)
                    if nao_msg:
                        await send_private_msg(MASTER_QQ, nao_msg, cfg.active_ws_qq)
                else:
                    img_fp = await fetch_and_save_acg_image()
                    img_msg = make_image_msg(img_fp)
                    if img_msg and cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):
                        await send_private_msg(MASTER_QQ, img_msg, cfg.active_ws_qq)
                cfg.daily_trigger.add(nao_birthday_key)
                log_system("奈绪生日快乐！")

            # ---------- 代码模式30分钟超时自动退出 ----------
            if cfg.CODE_MODE and cfg.CODE_MODE_LAST_MSG_TIME > 0:
                if _time.time() - cfg.CODE_MODE_LAST_MSG_TIME > cfg.CODE_MODE_TIMEOUT:
                    cfg.CODE_MODE = False
                    cfg.CODE_MODE_LAST_MSG_TIME = 0
                    log_system("代码模式超时自动退出（30分钟无消息）")
                    # 通知主人代码模式已自动退出
                    try:
                        if cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):
                            await send_private_msg(MASTER_QQ, [{"type": "text", "data": {"text": "⏰ 代码模式已因30分钟无消息自动退出，恢复人设回复"}}], cfg.active_ws_qq)
                    except Exception as notify_e:
                        log_err(f"代码模式超时退出通知失败: {notify_e}")

            # ---------- 任务触发 ----------
            for task in SCHEDULE_TASKS:
                key = f"{task['scene']}_{today}"
                if key in cfg.daily_trigger:
                    continue
                if today.weekday() not in task["weekday"]:
                    continue
                # 仅节假日任务（周末吐槽赖床），工作日跳过
                if task.get("only_holiday") and _is_workday:
                    continue
                tm = cfg.task_trigger_minute.get(key)
                if tm is None or cur_minute != tm:
                    continue

                # ★ 修复：先标记任务已触发，防止异常导致重复触发
                cfg.daily_trigger.add(key)
                log_system(f"定时:{task['scene']}")

                # 执行任务（用随机自然提示让AI以女友身份主动发起对话，每次不一样）
                try:
                    if task["scene"] == "催起床":
                        prompt = random.choice([
                            "现在是早上，该催主人起床了，你主动发消息给他",
                            "早上好，主人还在睡懒觉，你叫他起床",
                            "天亮了，主人还没醒，你去喊他起床",
                        ])
                        rep = await get_character_reply(prompt, str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                        img_fp = await fetch_and_save_acg_image()
                        img_msg = make_image_msg(img_fp)
                        if img_msg and cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):
                            await send_private_msg(MASTER_QQ, img_msg, cfg.active_ws_qq)
                            log_system("ACG起床图已发送")
                    elif task["scene"] == "催睡觉":
                        prompt = random.choice([
                            "夜深了，该催主人睡觉了，你主动发消息给他",
                            "很晚了，主人还没睡，你催他去睡觉",
                            "已经深夜了，主人还在熬夜，你叫他早点休息",
                        ])
                        rep = await get_character_reply(prompt, str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                        img_fp = await fetch_and_save_acg_image()
                        img_msg = make_image_msg(img_fp)
                        if img_msg and cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):
                            await send_private_msg(MASTER_QQ, img_msg, cfg.active_ws_qq)
                            log_system("ACG催睡图已发送")
                    else:
                        # 其他定时任务：每次用不同的自然提示
                        scene_prompts = {
                            "周末吐槽赖床": [
                                "周末了，主人还在睡懒觉，你主动吐槽他",
                                "休息日了，主人还没起床，你去调侃他一下",
                            ],
                            "提醒点外卖": [
                                "中午了，提醒主人该点外卖了，你主动发消息",
                                "到饭点了，主人还没吃饭，你催他去吃饭",
                            ],
                            "叮嘱午睡": [
                                "中午了，叮嘱主人睡个午觉，你主动发消息",
                                "午休时间到了，提醒主人休息一下，你主动说",
                            ],
                            "提醒起身": [
                                "下午了，提醒主人起来活动活动，你主动发消息",
                                "坐太久了，叫主人起来走走，你主动说",
                            ],
                            "提醒晚餐": [
                                "晚上了，提醒主人该吃晚饭了，你主动发消息",
                                "到晚饭时间了，主人还没吃，你催他去吃饭",
                            ],
                            "周日复盘": [
                                "周日晚上了，回顾这一周：问问他这周过得怎么样，也说说你自己这周的事",
                                "一周要结束了，跟主人聊聊这周发生的事，别像做汇报",
                            ],
                        }
                        prompts = scene_prompts.get(task["scene"], ["你主动找主人聊聊天"])
                        prompt = random.choice(prompts)
                        rep = await get_character_reply(prompt, str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                except Exception as task_e:
                    log_err(f"定时任务执行异常({task['scene']}):{task_e}")

            # ---------- 日程 / 待办检查（每 30 秒一次，别每秒查库） ----------
            if (_time.time() - _last_due_check) > 30:
                _last_due_check = _time.time()
                await process_due(now)

            # ---------- v16：空闲时自己读小说（后台跑，不堵定时循环） ----------
            _dispatch_reading(now)

            # ---------- 主动闲聊触发 ----------
            await maybe_chat(now)

        except Exception as e:
            log_err(f"定时异常:{e}")

        await asyncio.sleep(1)

# ===================== 空闲读书（v16） =====================

READ_CHECK_INTERVAL = 1800   # 30 分钟最多检查一次
_last_read_check = 0.0


async def maybe_read(now=None, force=False):
    """空闲时读一章小说；返回是否真的读了

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