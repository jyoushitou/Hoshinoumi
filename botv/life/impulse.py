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
                     lonely_threshold=None, daily_cap=None, require_lonely=True):
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

    # 2) 刚聊过（承诺回访/时间锚点不受这条限制——本来就是约好的）
    now_ts = _time.time()
    if require_lonely and last_user_ts and (now_ts - last_user_ts) < QUIET_AFTER_TALK_MIN * 60:
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

    # 5) 孤独不够（只有"想念"这一类才看孤独）
    if not require_lonely:
        return True, "按约定主动"

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


# ===================== 主动闲聊：30 分钟一次的冲动（v10.4） =====================
# 不再预设「今天 2~4 个时刻」，改成每 30 分钟问一次「现在想不想说话」。
# 概率随时间爬升——像人憋久了会忍不住，而不是到点打卡。

HOUR_WEIGHTS = [  # (起始小时, 结束小时, 权重)
    (0, 7, 0.0),     # 睡觉
    (7, 8, 0.02),
    (8, 9, 0.05),    # 刚起床
    (9, 12, 0.03),   # 上午在忙
    (12, 14, 0.10),  # 午休
    (14, 18, 0.03),  # 下午
    (18, 20, 0.12),  # 傍晚
    (20, 22, 0.08),
    (22, 23, 0.08),  # 睡前
    (23, 24, 0.0),
]

CHAT_MAX_P = 0.35          # 单次掷骰的上限
SILENCE_FULL_HOURS = 3.0   # 静默到这个时长，因子到 1
LIFE_EVENT_BOOST = 1.8     # 今天有事想分享


def hour_weight(hour):
    for start, end, w in HOUR_WEIGHTS:
        if start <= hour < end:
            return w
    return 0.0


def chat_probability(now=None, silent_hours=0.0, state=None, has_life_event=False):
    """这一次（30 分钟窗口）她开口的概率"""
    now = now or datetime.now(CST)
    weight = hour_weight(now.hour)
    if weight <= 0:
        return 0.0

    silence = min(1.0, max(0.0, silent_hours) / SILENCE_FULL_HOURS)
    state = state or {}
    lonely = float(state.get("lonely", 0.2))
    mood = float(state.get("mood", 0.1))
    mood_f = 1.1 if mood > 0.4 else (0.7 if mood < -0.2 else 1.0)

    p = weight * silence * (0.5 + lonely) * mood_f
    if has_life_event:
        p *= LIFE_EVENT_BOOST
    return min(CHAT_MAX_P, p)


def should_chat(now=None, rng=None, state=None, silent_hours=None,
                has_life_event=False, last_user_ts=None, last_proactive_ts=None,
                proactive_count=None, unanswered=None, daily_cap=None):
    """每 30 分钟问一次：现在主动说话吗？返回 (要不要, 原因, 概率)"""
    now = now or datetime.now(CST)
    rng = rng or random
    from ..core import state as cfg

    if state is None:
        state = life_current(now)
    if last_user_ts is None:
        last_user_ts = getattr(cfg, "last_user_msg_ts", 0.0)
    if proactive_count is None:
        proactive_count = getattr(cfg, "proactive_count_today", 0)
    if unanswered is None:
        unanswered = getattr(cfg, "proactive_unanswered", 0)
    if last_proactive_ts is None:
        last_proactive_ts = getattr(cfg, "last_proactive_ts", 0.0)
    cap = DAILY_CAP if daily_cap is None else daily_cap

    now_ts = _time.time()

    # 深夜不打扰（权重为 0 兜底）
    if hour_weight(now.hour) <= 0:
        return False, "深夜", 0.0

    # 刚聊过
    if last_user_ts and (now_ts - last_user_ts) < QUIET_AFTER_TALK_MIN * 60:
        return False, "刚聊过", 0.0

    # 今日配额
    if last_proactive_ts:
        try:
            same_day = datetime.fromtimestamp(last_proactive_ts, CST).date() == now.date()
        except (OSError, ValueError, OverflowError):
            same_day = False
        if same_day and proactive_count >= cap:
            return False, "今日配额用完", 0.0

    # 连续没回应
    if unanswered >= UNANSWERED_LIMIT:
        return False, "连续没回应", 0.0

    if silent_hours is None:
        silent_hours = ((now_ts - last_user_ts) / 3600.0) if last_user_ts else 24.0

    p = chat_probability(now, silent_hours, state, has_life_event)
    if p <= 0:
        return False, "时段不合适", 0.0
    if rng.random() > p:
        return False, f"没掷中(p={p:.1%})", p
    return True, f"想说话了(p={p:.1%})", p
