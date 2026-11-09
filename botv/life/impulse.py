# ===================== 主动冲动（v10-U9） =====================
# 要不要主动找你说句话？
#
# 以前是「每天随机挑 2~4 个时刻，到点就发」；现在是「到点问一次：她现在想不想说话」。
# 判定顺序：深夜 → 刚聊过 → 今日配额 → 连续没回应 → 孤独够不够 → 概率

import random
import time as _time
from datetime import datetime

from ..config import CST
from .state import current as life_current

DAILY_CAP = 3            # 每天主动消息上限（所有由头共享）
LONELY_THRESHOLD = 0.45  # 孤独到这个程度才想开口
QUIET_AFTER_TALK_MIN = 25  # 刚聊过这么多分钟就别打扰
QUIET_START_HOUR = 23    # 深夜静默
QUIET_END_HOUR = 7
UNANSWERED_LIMIT = 2     # 连着几条没人理就别再说

PROB_BASE = 0.35         # 刚过阈值时的触发概率
PROB_GAIN = 1.4          # 孤独每高 0.1，概率加多少
PROB_MAX = 0.85


def _in_quiet_hours(now):
    return now.hour >= QUIET_START_HOUR or now.hour < QUIET_END_HOUR


def should_reach_out(now=None, state=None, rng=None,
                     last_user_ts=None, last_proactive_ts=None,
                     proactive_count=None, unanswered=None,
                     lonely_threshold=None, daily_cap=None):
    """返回 (要不要发, 原因)

    参数都可注入，方便测试；不传就从全局状态里读。
    """
    now = now or datetime.now(CST)
    rng = rng or random

    from ..core import state as cfg
    if state is None:
        state = life_current(now)
    if last_user_ts is None:
        last_user_ts = getattr(cfg, "last_user_msg_ts", 0.0)
    if last_proactive_ts is None:
        last_proactive_ts = getattr(cfg, "last_proactive_ts", 0.0)
    if proactive_count is None:
        proactive_count = getattr(cfg, "proactive_count_today", 0)
    if unanswered is None:
        unanswered = getattr(cfg, "proactive_unanswered", 0)

    threshold = LONELY_THRESHOLD if lonely_threshold is None else lonely_threshold
    cap = DAILY_CAP if daily_cap is None else daily_cap

    # 1) 深夜不打扰
    if _in_quiet_hours(now):
        return False, "深夜"

    # 2) 刚聊过
    now_ts = _time.time()
    if last_user_ts and (now_ts - last_user_ts) < QUIET_AFTER_TALK_MIN * 60:
        return False, "刚聊过"

    # 3) 今日配额
    if last_proactive_ts:
        try:
            same_day = datetime.fromtimestamp(last_proactive_ts, CST).date() == now.date()
        except (OSError, ValueError, OverflowError):
            same_day = False  # 时间戳坏了就当不是今天，别崩
        if same_day and proactive_count >= cap:
            return False, "今日配额用完"

    # 4) 连续没回应
    if unanswered >= UNANSWERED_LIMIT:
        return False, "连续没回应"

    # 5) 孤独不够
    lonely = float(state.get("lonely", 0.0))
    if lonely < threshold:
        return False, f"不想说话(孤独{lonely:.2f})"

    # 6) 概率闸门：孤独越高越想说
    p = min(PROB_MAX, PROB_BASE + (lonely - threshold) * PROB_GAIN)
    if rng.random() > p:
        return False, "这次算了"

    return True, f"想说话了(孤独{lonely:.2f}, p={p:.2f})"


def note_user_message():
    """收到用户消息：记下时间，并清空未回应计数"""
    from ..core import state as cfg
    cfg.last_user_msg_ts = _time.time()
    cfg.proactive_unanswered = 0


def note_proactive():
    """发出了一条主动消息"""
    from ..core import state as cfg
    now = _time.time()
    today = datetime.now(CST).date()
    last = float(getattr(cfg, "last_proactive_ts", 0.0))
    try:
        if last and datetime.fromtimestamp(last, CST).date() != today:
            cfg.proactive_count_today = 0  # 跨天重置
    except (OSError, ValueError, OverflowError):
        cfg.proactive_count_today = 0
    cfg.last_proactive_ts = now
    cfg.proactive_count_today = getattr(cfg, "proactive_count_today", 0) + 1
    cfg.proactive_unanswered = getattr(cfg, "proactive_unanswered", 0) + 1


def _reset_daily():
    """跨天重置计数（由定时任务在切日时调用）"""
    from ..core import state as cfg
    cfg.proactive_count_today = 0
