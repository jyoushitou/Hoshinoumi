# ===================== 关系里程碑（v12-G38） =====================
# 认识第几天。平常不提，特殊日子她才说一句。
#
# 「认识」从第一次和她说话那天算——所以首次交互时要记下 since。

import json
from datetime import date, datetime

from ..config import CST

# 值得提一句的日子（其余的天数不提）
MILESTONES = {
    1: "认识的第一天",
    7: "认识满一周",
    30: "认识一个月",
    100: "认识一百天",
    200: "认识两百天",
    365: "认识满一年",
    500: "认识五百天",
    730: "认识满两年",
}


def _today(now=None):
    return (now or datetime.now(CST)).date()


def _load_raw(tid):
    try:
        from ..infra.repo_memory import load_relation
        raw = load_relation(str(tid))
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _save_raw(tid, data):
    try:
        from ..infra.repo_memory import save_relation
        save_relation(str(tid), json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        return True
    except Exception:
        return False


def since_date(tid, now=None):
    """第一次说话那天；没有就记成今天"""
    data = _load_raw(tid)
    raw = data.get("since")
    if raw:
        try:
            return date.fromisoformat(raw)
        except Exception:
            pass
    today = _today(now)
    data["since"] = today.isoformat()
    _save_raw(tid, data)
    return today


def days_together(tid, now=None):
    """认识第几天（含今天）"""
    start = since_date(tid, now)
    return max(1, (_today(now) - start).days + 1)


def milestone_text(tid, now=None):
    """今天是不是特殊日子；不是就返回空串"""
    try:
        days = days_together(tid, now)
    except Exception:
        return ""
    if days in MILESTONES:
        return f"今天正好{MILESTONES[days]}（第 {days} 天）"
    if days > 365 and days % 100 == 0:
        return f"今天正好认识第 {days} 天"
    return ""


def is_milestone(tid, now=None):
    return bool(milestone_text(tid, now))
