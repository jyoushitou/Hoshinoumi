# ===================== 回复时机（v6-A1） =====================
# 人不会秒回。按「时段 + 随机」决定等多久再回，命令除外。

import random
from datetime import datetime

from ..config import CST

# (起始小时, 结束小时, 最短秒, 最长秒)
BANDS = [
    (0, 6, 20, 180),    # 凌晨：很慢，可能睡着了
    (6, 9, 10, 60),     # 清晨：刚醒
    (9, 18, 5, 30),     # 白天：有空，回得快
    (18, 23, 8, 60),    # 晚上：在忙别的
    (23, 24, 20, 120),  # 深夜：困
]

DEFAULT_BAND = (5, 30)


def delay_range(now=None):
    """按当前时段返回 (最短, 最长) 秒"""
    now = now or datetime.now(CST)
    h = now.hour
    for start, end, lo, hi in BANDS:
        if start <= h < end:
            return lo, hi
    return DEFAULT_BAND


def reply_delay(now=None, rng=None):
    """算一个延迟秒数

    用平方压向短的一端：大多数时候几秒就回，偶尔才拖很久。
    这样更像「正好在看手机」而不是「每次都在忙」。
    """
    lo, hi = delay_range(now)
    rng = rng or random
    return lo + (hi - lo) * (rng.random() ** 2)


# ===================== 语气提示（v6-A20） =====================
# 现在还没有 mood 状态（v9 才有），先用时段近似「她现在什么状态」
TONES = [
    (0, 6, "现在是深夜，你有点困：句子要短，多用省略号，别长篇大论。"),
    (6, 9, "现在是清晨，你刚醒：语气懒懒的，话不多，偶尔敷衍。"),
    (9, 18, "现在是白天，你精神不错：正常说话，可以多说两句。"),
    (18, 23, "现在是晚上，你比较放松：语气软一点，可以贫两句。"),
    (23, 24, "已经过了 23 点，你困了：句子短，偶尔走神、漏字。"),
]


def tone_hint(now=None):
    """按时段给一句语气提示（v6-A20）"""
    now = now or datetime.now(CST)
    h = now.hour
    for start, end, hint in TONES:
        if start <= h < end:
            return hint
    return "正常说话。"
