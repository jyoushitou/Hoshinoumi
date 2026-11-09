# ===================== 定时任务配置 =====================
# 工作日判断 + 任务表
# 迁移自 schedule.py（v5-R5）

from datetime import date, time

# 工作日判断（chinesecalendar 可选）
try:
    from chinesecalendar import is_workday as _is_workday  # 法定工作日判断
    CHINESE_CALENDAR_OK = True  # 库可用标志
except Exception:
    CHINESE_CALENDAR_OK = False  # 库未安装，降级使用 weekday 判断


def is_workday_today():
    """判断今天是否是法定工作日，使用 chinesecalendar 库"""
    if CHINESE_CALENDAR_OK:
        try:
            return _is_workday(date.today())
        except Exception:
            pass
    return date.today().weekday() < 5


# 定时任务配置
# weekday: 0=周一 ... 6=周日
# 催起床特殊：工作日7:30，非工作日8:30
# 周末吐槽赖床仅非工作日触发（用 is_workday_today 动态判断，涵盖周末+法定节假日）
SCHEDULE_TASKS = [
    {"scene": "催起床", "weekday": [0, 1, 2, 3, 4, 5, 6]},
    {"scene": "周末吐槽赖床", "weekday": [0, 1, 2, 3, 4, 5, 6], "t": time(8, 30), "only_holiday": True},
    {"scene": "提醒点外卖", "weekday": [0, 1, 2, 3, 4, 5, 6], "t": time(10, 40)},
    {"scene": "叮嘱午睡", "weekday": [0, 1, 2, 3, 4, 5, 6], "t": time(12, 30)},
    {"scene": "提醒起身", "weekday": [0, 1, 2, 3, 4, 5, 6], "t": time(13, 30)},
    {"scene": "提醒晚餐", "weekday": [0, 1, 2, 3, 4, 5, 6], "t": time(16, 40)},
    {"scene": "催睡觉", "weekday": [0, 1, 2, 3, 4, 5, 6]},
    {"scene": "周日复盘", "weekday": [6], "t": time(21, 0)},  # v12-G45：周日晚上回顾这一周
]
