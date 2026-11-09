# ===================== 定时任务主循环 =====================
# 跨天初始化、生日、自动日记、代码模式超时、任务触发、主动闲聊
# 迁移自 schedule.py（v5-R5），逻辑逐字未改

import asyncio
import random
import time as _time
from datetime import datetime, timedelta

from ..config import MASTER_QQ, CST
from botv.core import state as cfg
from ..log import log_system, log_err
from ..ai.client import get_character_reply
from ..memory import add_target_memory
from ..chat.send import send_short_reply, send_private_msg
from ..image import fetch_and_save_acg_image, search_local_image_by_tags, get_best_image
from ..utils import make_image_msg
from ..ai.parse import parse_ai_reply
from ..diary import generate_diary
from ..infra.repo_memory import load_events_from_db
from .config import SCHEDULE_TASKS, is_workday_today
from .planner import calc_day_tasks

# 每天首次运行的延迟（秒），用于跨天精确触发
_FIRST_RUN_DELAY = 10


class _SkipChat(Exception):
    """这次不主动发（内部信号，不打印任何东西）"""


async def cycle_task_run():
    await asyncio.sleep(_FIRST_RUN_DELAY)
    _last_today = None  # 记录上一次检查的日期
    _is_workday = True  # 缓存当天是否工作日
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

                # ===== 所有主动消息（定时任务+闲聊）合并排序，确保间隔至少1小时 =====
                # 1. 先收集所有定时任务的触发分钟
                all_active_minutes = set()
                for key, tm in cfg.task_trigger_minute.items():
                    if 480 <= tm <= 1380:  # 只保留你醒着的时间段 8:00~23:00
                        all_active_minutes.add(tm)

                # 2. 生成随机闲聊触发时间点（2~4次），确保与定时任务间隔 >= 60分钟
                chat_count = random.randint(2, 4)
                available_minutes = list(range(480, 1381))  # 8:00~23:00
                # 移除定时任务前后60分钟的时间点
                for tm in all_active_minutes:
                    remove_start = max(480, tm - 60)
                    remove_end = min(1380, tm + 60)
                    available_minutes = [m for m in available_minutes if m < remove_start or m > remove_end]

                chat_times = []
                for _ in range(chat_count):
                    if not available_minutes:
                        break
                    chosen = random.choice(available_minutes)
                    chat_times.append(chosen)
                    # 移除 chosen 前后60分钟内的所有时间点，确保闲聊之间也间隔
                    remove_start = max(480, chosen - 60)
                    remove_end = min(1380, chosen + 60)
                    available_minutes = [m for m in available_minutes if m < remove_start or m > remove_end]

                cfg.daily_chat_trigger_times = sorted(chat_times)

                # 3. 合并所有主动消息时间点并排序，用于间隔检查
                all_active = sorted(set(list(all_active_minutes) + cfg.daily_chat_trigger_times))
                log_system(f"所有主动消息时间点: {[f'{m//60:02d}:{m%60:02d}' for m in all_active]}")
                log_system(f"其中主动闲聊: {[f'{m//60:02d}:{m%60:02d}' for m in cfg.daily_chat_trigger_times]}")
                _last_today = today
                log_system(f"定时任务初始化完成，共 {len(cfg.task_trigger_minute)} 个任务点")

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
                        }
                        prompts = scene_prompts.get(task["scene"], ["你主动找主人聊聊天"])
                        prompt = random.choice(prompts)
                        rep = await get_character_reply(prompt, str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                except Exception as task_e:
                    log_err(f"定时任务执行异常({task['scene']}):{task_e}")

            # ---------- 日程提醒（v10-U10） ----------
            try:
                for it in agenda_due_soon(60):
                    ok, why = should_reach_out(now=now, require_lonely=False)
                    if not ok:
                        continue
                    rep = await get_character_reply(
                        f"（提醒他：{it.get('t', '')}。一句话，别说教。）",
                        str(MASTER_QQ))
                    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                    note_proactive()
                    agenda_mark(it["id"])
                    log_system(f"日程已提醒: {it.get('t', '')[:20]}")
            except Exception as a_e:
                log_err(f"日程提醒异常:{a_e}")

            # ---------- 待办到点：回访承诺 / 时间锚点（v10-U9b） ----------
            try:
                for item_id, item in pending_due(now):
                    ok, why = should_reach_out(now=now, require_lonely=False)
                    if not ok:
                        log_api(f"待办暂缓({why}): {item.get('t')}")
                        continue
                    rep = await get_character_reply(
                        f"（{describe_pending(item)}。就一句话，别解释，别问他在干嘛。）",
                        str(MASTER_QQ))
                    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                    note_proactive()
                    finish_pending(item_id)
                    log_system(f"待办已回访: {item.get('t')}")
            except Exception as p_e:
                log_err(f"待办处理异常:{p_e}")

            # ---------- 主动闲聊触发（基于事件记忆，让AI自己发挥） ----------
            if (cur_minute in cfg.daily_chat_trigger_times and
                    cur_minute not in cfg.triggered_today):
                # ★ 修复：先标记已触发，防止异常导致重复触发
                cfg.triggered_today.add(cur_minute)
                try:
                    # v10-U9：先问她想不想说话，不想就跳过
                    ok, why = should_reach_out(now=now)
                    if not ok:
                        log_system(f"主动闲聊跳过: {why}")
                        raise _SkipChat()
                    # v10-U9b：心情很差时只说一句，不解释
                    try:
                        from ..life.state import current as life_current
                        mood_now = float(life_current().get("mood", 0.0))
                    except Exception:
                        mood_now = 0.0
                    if mood_now < -0.5:
                        log_system(f"主动闲聊（心情差 {mood_now:.2f}，只说一句）")
                        rep = await get_character_reply(
                            "（你现在心情很差，只发一句很短的话，不解释原因，也别问他在干嘛）",
                            str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                        note_proactive()
                        raise _SkipChat()

                    # v10-U9b：一半概率分享今天的生活事件
                    life_today = load_today_life()
                    if life_today and random.random() < 0.5:
                        seed = random.choice(life_today)
                        log_system(f"主动闲聊触发（分享生活: {seed[:20]}）")
                        rep = await get_character_reply(
                            f"（主动找他说话。说说你今天的这件事：{seed}。别问他在不在，直接说事。）",
                            str(MASTER_QQ))
                        await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                        note_proactive()
                        raise _SkipChat()

                    # 从数据库加载最近的事件作为话题
                    recent_events = load_events_from_db(str(MASTER_QQ), limit=5)
                    if recent_events:
                        # 有事件记忆时，把事件传给AI，让AI自己决定怎么接着聊
                        chosen_event = random.choice(recent_events)[0]
                        log_system(f"主动闲聊触发（基于事件: {chosen_event}）")
                        rep = await get_character_reply(f"闲聊（之前{chosen_event}）", str(MASTER_QQ))
                    else:
                        # 没有事件时直接传闲聊
                        log_system(f"主动闲聊触发（无事件）")
                        rep = await get_character_reply("闲聊", str(MASTER_QQ))
                    await send_short_reply(MASTER_QQ, rep, cfg.active_ws_qq, MASTER_QQ)
                    note_proactive()  # v10-U9：记账，配额和未回应计数
                    log_system(f"主动闲聊触发完成")
                except _SkipChat:
                    pass
                except Exception as chat_e:
                    log_err(f"主动闲聊执行异常:{chat_e}")

        except Exception as e:
            log_err(f"定时异常:{e}")

        await asyncio.sleep(1)
