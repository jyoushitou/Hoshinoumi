# ===================== 对话里提取定时任务（v17.7） =====================
# 「明天七点叫我」「每晚十一点提醒我睡觉」「周五提醒我交报告」
#   → 解析成 cron_tasks 的一行
#
# 原则（见 v17.6 计划「两种建立方式」）：
#   - 只从主人私聊提取
#   - 一次只建一条
#   - 时间说不清就不建
#   - 5 分钟内同内容去重

import re
import time
from datetime import datetime, timedelta

from ..core import clock

# 时间词
_CN_NUM = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
           "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
           "十一": 11, "十二": 12}
_WEEKDAY = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "日": 7, "天": 7}

# 动作词：有这些词才认为「他想让我做事」
_ACTION = ("叫", "提醒", "通知", "喊", "告诉", "记得", "别忘")

_recent = {}      # 去重：内容 -> ts
DEDUPE_WINDOW = 300
DEFAULT_HOUR = 9        # 周几没说几点时默认 09:00

# v18.7：能按天微调的场景
_SCENE_WORDS = (
    ("叫午睡起床", ("午睡", "午觉")),
    ("催睡觉", ("睡觉", "睡了", "催我睡", "睡")),
    ("催起床", ("起床", "叫我", "叫醒", "喊我")),
    ("提醒晚餐", ("晚饭", "晚餐", "吃饭")),
)
_SKIP_WORDS = ("别叫", "不用叫", "取消", "不用提醒", "别提醒")


def _norm_num(s):
    """十二 / 7 / 两 → int"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    return _CN_NUM.get(s)


def _cn_int(s):
    """中文数字 → int：三十 → 30，十五 → 15，七 → 7"""
    s = (s or "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s in _CN_NUM:
        return _CN_NUM[s]
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CN_NUM.get(left, 1) if left else 1
        ones = _CN_NUM.get(right, 0) if right else 0
        return tens * 10 + ones
    return None


def parse_time(text, now=None):
    """从一句话里解析时间，返回 (schedule_type, kwargs) 或 None

    支持：
      每天/每晚 HH点[半|MM分]      → daily
      周X/星期X [HH点]             → weekly
      明天/今晚 HH点               → once
      N分钟后 / 半小时后            → once（相对）
    """
    now = now or clock.naive()
    text = (text or "").strip()
    if not text:
        return None

    # 相对时间：N分钟后 / 半小时后
    m = re.search(r"([0-9]+|[一二两三四五六七八九十]+|半)\s*分钟后", text)
    if m:
        raw = m.group(1)
        mins = 30 if raw == "半" else _cn_int(raw)
        if mins is None:
            return None
        at = now + timedelta(minutes=int(mins))
        return ("once", {"once_at": at.strftime("%Y-%m-%d %H:%M:%S")})
    if "半小时后" in text:
        at = now + timedelta(minutes=30)
        return ("once", {"once_at": at.strftime("%Y-%m-%d %H:%M:%S")})

    # 找钟点：七点 / 7点 / 七点半 / 7:30
    hour, minute = None, 0
    m = re.search(r"([0-9]{1,2}|十[一二]?|[零一二两三四五六七八九])\s*[:：]\s*([0-9]{2})", text)
    if m:
        hour, minute = _norm_num(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"([0-9]{1,2}|十[一二]?|[零一二两三四五六七八九])\s*点\s*(半|[0-9]{1,2}\s*分)?", text)
        if m:
            hour = _norm_num(m.group(1))
            if m.group(2) == "半":
                minute = 30
            elif m.group(2):
                minute = _norm_num(m.group(2).replace("分", "").strip())

    # 周几：没写钟点就用默认 09:00
    m_week = re.search(r"(?:周|星期)([一二三四五六日天])", text)
    if m_week:
        hh = hour if hour is not None else DEFAULT_HOUR
        return ("weekly", {"at_time": f"{hh:02d}:{minute:02d}",
                           "weekdays": str(_WEEKDAY[m_week.group(1)])})

    if hour is None or not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    # 「晚上十一点」= 23:00；「凌晨两点」= 02:00
    if any(w in text for w in ("晚上", "晚", "夜里", "夜间")) and hour < 12:
        hour += 12
    elif "下午" in text and hour < 12:
        hour += 12
    elif "凌晨" in text and hour == 12:
        hour = 0


    # 明天 / 今晚 → once
    if "明天" in text:
        at = (now + timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        return ("once", {"once_at": at.strftime("%Y-%m-%d %H:%M:%S")})
    if "今晚" in text or "今天晚上" in text:
        at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if at <= now:
            at += timedelta(days=1)
        return ("once", {"once_at": at.strftime("%Y-%m-%d %H:%M:%S")})

    # 每天 / 每晚
    if any(w in text for w in ("每天", "每晚", "天天")):
        return ("daily", {"at_time": f"{hour:02d}:{minute:02d}"})

    # 只说钟点：当成今天/明天的那一次
    at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if at <= now:
        at += timedelta(days=1)
    return ("once", {"once_at": at.strftime("%Y-%m-%d %H:%M:%S")})


def parse_content(text):
    """把时间词和动作词剥掉，剩下的就是「要提醒什么」"""
    s = (text or "").strip()
    # 去时间描述
    s = re.sub(r"[下这本]\s*(?=周|星期)", "", s)
    s = re.sub(r"(明天|今晚|每天晚上|每晚|每天|天天|周[一二三四五六日天]|星期[一二三四五六日天])", "", s)
    s = re.sub(r"[0-9]{1,2}\s*[:：]\s*[0-9]{2}", "", s)
    s = re.sub(r"([0-9]{1,2}|十[一二]?|[零一二两三四五六七八九])\s*点(半|[0-9]{1,2}\s*分)?", "", s)
    s = re.sub(r"([0-9]+|[一二两三四五六七八九十]+|半)\s*分钟后|半小时后", "", s)
    s = re.sub(r"[下这本]\s*(?=周|星期)", "", s)
    # 去动作词
    for w in _ACTION:
        s = s.replace(w, "")
    s = s.replace("我", "").replace("你", "")
    s = re.sub(r"^[，。,.！!\s]+|[，。,.！!\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s:
        return s
    # 兜底：原句里只剥时间词，保留「叫我」这种动词
    fb = re.sub(r"(明天|今晚|每天晚上|每晚|每天|天天|周[一二三四五六日天]|"
                r"星期[一二三四五六日天]|[下这本]\s*(?=周|星期)|"
                r"[0-9]+\s*分钟后|"
                r"([一二两三四五六七八九十]+|半)\s*分钟后|半小时后|"
                r"[0-9]{1,2}\s*[:：]\s*[0-9]{2}|"
                r"([0-9]{1,2}|十[一二]?|[零一二两三四五六七八九])\s*点(半|[0-9]{1,2}\s*分)?)",
                "", text or "")
    fb = re.sub(r"^[，。,.！!\s]+|[，。,.！!\s]+$", "", fb)
    return fb or "提醒你"


def extract(text, now=None):
    """从一句话里提取定时任务；返回 dict 或 None

    {"schedule_type","at_time","weekdays","once_at","content"}
    """
    text = (text or "").strip()
    if not text:
        return None
    # 必须像「要求她做事」
    if not any(w in text for w in _ACTION):
        return None

    parsed = parse_time(text, now)
    if not parsed:
        return None
    stype, kwargs = parsed
    content = parse_content(text)
    kwargs.update({"schedule_type": stype, "content": content})
    return kwargs


def should_extract(message_type, text, uid=None, master=None):
    """哪些消息值得尝试提取"""
    if message_type != "private":
        return False
    if master and str(uid) != str(master):
        return False
    text = (text or "").strip()
    if not text or text.startswith("!"):
        return False
    return any(w in text for w in _ACTION)


def dedupe_ok(content):
    """5 分钟内同内容只建一次"""
    now = time.time()
    last = _recent.get(content, 0)
    if now - last < DEDUPE_WINDOW:
        return False
    _recent[content] = now
    return True


def _scene_for(text):
    for scene, words in _SCENE_WORDS:
        if any(w in text for w in words):
            return scene
    return None


def parse_override(text, now=None):
    """v18.7：今天/今晚/明天 + 场景 → 当天覆盖（不是新建任务）"""
    now = now or clock.naive()
    text = (text or "").strip()
    if not text:
        return None
    if not any(w in text for w in ("今天", "今晚", "明天")) and not any(
            w in text for w in _SKIP_WORDS):
        return None
    scene = _scene_for(text)
    if not scene:
        return None

    skip = any(w in text for w in _SKIP_WORDS)
    parsed = parse_time(text, now)
    at_time = None
    day = now.date()
    if "明天" in text:
        day = (now + timedelta(days=1)).date()
    elif "今天" in text or "今晚" in text:
        day = now.date()

    if parsed:
        stype, kwargs = parsed
        if stype != "once":
            return None
        once_at = kwargs.get("once_at") or ""
        try:
            dt = datetime.strptime(once_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        at_time = dt.strftime("%H:%M")
        if "今天" not in text and "今晚" not in text and "明天" not in text:
            day = dt.date()

    if not at_time and not skip:
        return None
    return {"scene": scene, "day": day, "at_time": at_time, "skip": skip,
            "content": parse_content(text)}


def create_from_text(text, uid, now=None, add_func=None):
    """解析 + 入库 + 挂钩子；返回 (task_id, kwargs) 或 (None, None)"""
    # v18.7：今天/明天 + 场景 → 只改当天，不新建任务
    ov = parse_override(text, now)
    if ov:
        try:
            from ..schedule import cron
            ok = cron.add_override(str(uid), ov["scene"], ov["day"],
                                   at_time=ov["at_time"], skip=ov["skip"],
                                   source="chat", note=text[:80])
            if ok:
                data = {
                    "schedule_type": "once",
                    "once_at": f"{ov['day']} {ov['at_time'] or '00:00'}:00",
                    "content": ov["content"],
                    "override_scene": ov["scene"],
                    "override_day": ov["day"].isoformat(),
                    "override_skip": ov["skip"],
                    "override_time": ov["at_time"],
                }
                try:
                    cron.schedule_all()
                except Exception:
                    pass
                return 0, data
        except Exception:
            pass

    data = extract(text, now)
    if not data:
        return None, None
    if not dedupe_ok(data["content"]):
        return None, data
    try:
        from ..schedule import cron

        add = add_func or cron.add
        tid = add(str(uid), data["schedule_type"], data["content"],
                  at_time=data.get("at_time"), weekdays=data.get("weekdays"),
                  once_at=data.get("once_at"), source="chat")
        if tid:
            try:
                cron.schedule_one(cron.get(tid))
            except Exception:
                pass
        return tid, data
    except Exception:
        return None, data

def describe(data, task_id=None):
    """把解析结果说成一句人话，用于回复确认"""
    if not data:
        return ""
    if data.get("override_scene"):
        scene = data.get("override_scene")
        day = data.get("override_day", "")
        if data.get("override_skip"):
            return f"好，{day} 不提醒{scene}（只改这一天）"
        return f"好，{day} {data.get('override_time')} 提醒{scene}（只改这一天）"
    kind = data.get("schedule_type")
    if kind == "daily":
        when = f"每天 {data.get('at_time')}"
    elif kind == "weekly":
        wd = {"1": "一", "2": "二", "3": "三", "4": "四",
              "5": "五", "6": "六", "7": "日"}
        days = str(data.get("weekdays") or "").replace(",", "")
        days = "".join(wd.get(c, c) for c in days) or "?"
        when = f"每周{days} {data.get('at_time')}"
    else:
        when = f"{data.get('once_at', '')[:16]}"
    tail = f"（#{task_id}，不想要就说 !cron del {task_id}）" if task_id else ""
    return f"好，{when} 提醒你{data.get('content', '')}{tail}"
