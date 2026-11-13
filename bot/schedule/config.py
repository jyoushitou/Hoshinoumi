# ===================== 定时任务配置 =====================
# 工作日判断 + 任务表
# 迁移自 schedule.py（v5-R5）

from datetime import date

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


# v18.9：SCHEDULE_TASKS 已删除——真实计划在 cron_tasks（!cron）

