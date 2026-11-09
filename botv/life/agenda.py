# ===================== 日程（v10-U10） =====================
# 从对话里认出「周五面试」这类话，变成一条带时间的待办，到点前提她一句。
#
# 解析原则：宁可少认，不可乱认——认错了她会提醒你一件没发生的事。

import calendar
import json
import re
from datetime import datetime, timedelta

from ..config import CST
from ..log import log_system

WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
          "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}

def _num(s):
    """中文数字或阿拉伯数字 → int"""
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    return CN_NUM.get(s) or 0

# 带时间跟事件同时出现才算日程
EVENT_WORDS = ["面试", "考试", "答辩", "开会", "会议", "约会", "体检", "交作业",
               "汇报", "演出", "比赛", "生日", "上课", "见家长", "报名", "截止"]

_DEFAULT_HOUR = 9  # 没说几点，默认当天上午 9 点


def _base(now):
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_when(text, now=None):
    """从一句话里解析出时间，解析不到返回 None"""
    now = now or datetime.now(CST)
    text = text or ""
    day = None

    if "后天" in text:
        day = _base(now) + timedelta(days=2)
    elif "明天" in text or "明日" in text:
        day = _base(now) + timedelta(days=1)
    elif "今天" in text or "今晚" in text:
        day = _base(now)
    else:
        # v14-C1：模糊说法
        if "月底" in text:
            last_day = calendar.monthrange(now.year, now.month)[1]
            day = _base(now).replace(day=last_day)
        elif "下个月" in text:
            y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
            day = datetime(y, m, 1, tzinfo=CST)
        elif "周末" in text:
            wd = now.weekday()
            if "下周末" in text:
                delta = (5 - wd) % 7 or 7
                delta += 7
            else:
                delta = 0 if wd >= 5 else (5 - wd)
            day = _base(now) + timedelta(days=delta)

        m = re.search(r"下?(?:周|星期|礼拜)([一二三四五六日天])", text)
        if m:
            target = WEEKDAYS[m.group(1)]
            today = now.weekday()
            delta = (target - today) % 7
            if delta == 0:
                delta = 7  # 说「周五」而今天周五，当作下周
            if "下" in m.group(0):
                delta = ((target - today) % 7) + 7 or 7
            day = _base(now) + timedelta(days=delta)
        else:
            m = re.search(r"(\d{1,2})月(\d{1,2})[日号]", text)
            if m:
                month, dom = int(m.group(1)), int(m.group(2))
                year = now.year
                try:
                    cand = datetime(year, month, dom, tzinfo=CST)
                    if cand < _base(now):
                        cand = datetime(year + 1, month, dom, tzinfo=CST)
                    day = cand
                except ValueError:
                    return None

    if day is None:
        return None

    hour = _DEFAULT_HOUR
    if "下午" in text or "晚上" in text or "今晚" in text:
        hour = 19
    elif "中午" in text:
        hour = 12
    elif "早上" in text or "上午" in text:
        hour = 9

    m = re.search(r"(?:早上|上午|中午|下午|晚上)?\s*(\d{1,2}|[一二两三四五六七八九十]{1,3})\s*[点:：]", text)
    if m:
        h = _num(m.group(1))
        if ("下午" in text or "晚上" in text or "今晚" in text) and h < 12:
            h += 12
        if 0 <= h <= 23:
            hour = h

    return day.replace(hour=hour)


def extract(text, now=None):
    """识别日程：必须同时有时间 + 事件词，返回 dict 或 None"""
    now = now or datetime.now(CST)
    text = text or ""
    if not any(w in text for w in EVENT_WORDS):
        return None
    when = parse_when(text, now)
    if when is None:
        return None
    if when.timestamp() < now.timestamp() - 60:  # 已经过去了，不记
        return None

    snippet = text.strip()
    if len(snippet) > 40:
        snippet = snippet[:39] + "…"
    return {"t": snippet, "due": when.timestamp()}


# ===================== 存取 =====================

def add(item):
    """写入一条日程"""
    try:
        from ..infra.repo_memory import add_event_to_db, STATE_TARGET
        add_event_to_db(STATE_TARGET, json.dumps(item, ensure_ascii=False),
                        tags="日程", kind="todo")
        log_system(f"日程已记下: {item.get('t', '')[:20]}")
        return True
    except Exception as e:
        log_system(f"日程写入失败: {e}")
        return False


def list_all():
    """未完成且没过去的日程"""
    from ..infra.repo_memory import load_todo_items
    now_ts = datetime.now(CST).timestamp()
    out = []
    try:
        rows = load_todo_items()
    except Exception:
        return out
    for row in rows:
        try:
            it = json.loads(row["event_summary"] or "{}")
        except Exception:
            continue
        if float(it.get("due", 0)) < now_ts - 86400:  # 过期一天以上
            continue
        out.append({"id": row["id"], **it})
    out.sort(key=lambda x: x.get("due", 0))
    return out


def due_soon(minutes=60):
    """一小时内要到点、还没提醒过的"""
    now_ts = datetime.now(CST).timestamp()
    out = []
    for it in list_all():
        if it.get("d"):  # 已提醒
            continue
        left = float(it.get("due", 0)) - now_ts
        if 0 <= left <= minutes * 60:
            out.append(it)
    return out


def mark_reminded(item_id):
    """标记已提醒"""
    from ..infra.repo_memory import load_todo_items, update_todo_item
    for row in load_todo_items():
        if row["id"] != item_id:
            continue
        try:
            it = json.loads(row["event_summary"] or "{}")
        except Exception:
            return
        it["d"] = 1
        try:
            update_todo_item(item_id, json.dumps(it, ensure_ascii=False))
        except Exception:
            pass
        return


def remove(item_id):
    try:
        from ..infra.repo_memory import delete_todo_item
        delete_todo_item(item_id)
        return True
    except Exception:
        return False
