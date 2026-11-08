# ===================== 时间表计算 =====================
# 计算每天各任务的触发分钟（带随机偏移）
# 迁移自 schedule.py（v5-R5）

import random
from datetime import date, timedelta

from .config import SCHEDULE_TASKS, CHINESE_CALENDAR_OK
from . import config as _cfg


def calc_day_tasks(today: date, is_workday: bool):
    """计算某一天所有任务的触发分钟（带随机偏移），返回 {key: minute}"""
    result = {}
    today_weekday = today.weekday()
    for task in SCHEDULE_TASKS:
        if today_weekday not in task["weekday"]:
            continue
        # 仅节假日触发的任务（周末吐槽赖床），工作日跳过
        if task.get("only_holiday") and is_workday:
            continue
        if task["scene"] == "催起床":
            base_h, base_m = (7, 30) if is_workday else (8, 30)
            base = base_h * 60 + base_m
        elif task["scene"] == "催睡觉":
            # 根据明天是否是工作日决定今晚催睡觉时间
            tomorrow = today + timedelta(days=1)
            if CHINESE_CALENDAR_OK:
                try:
                    tomorrow_workday = _cfg._is_workday(tomorrow)
                except Exception:
                    tomorrow_workday = tomorrow.weekday() < 5
            else:
                tomorrow_workday = tomorrow.weekday() < 5
            base_h, base_m = (23, 0) if tomorrow_workday else (23, 30)
            base = base_h * 60 + base_m
        else:
            base = task["t"].hour * 60 + task["t"].minute
        key = f"{task['scene']}_{today}"
        result[key] = max(0, min(1439, base + random.randint(-10, 10)))
    return result
