# ===================== 运行统计（v15） =====================
# 只统计当天，跨天自动清零。给 !stats 用，不改行为。

from datetime import date

COUNTERS = (
    "replies",        # 回复条数（一轮算一次）
    "images",         # 配图次数
    "voices",         # 语音次数
    "group_answer",   # 群里接话次数
    "group_skip",     # 群里跳过次数
    "proactive",      # 主动发出次数
    "digest",         # 浓缩写入次数
)

_data = {}
_day = None


def _roll():
    global _data, _day
    today = date.today()
    if _day != today:
        _day = today
        _data = {k: 0 for k in COUNTERS}


def inc(name, n=1):
    """计数 +1"""
    _roll()
    if name in _data:
        _data[name] += n


def snapshot():
    """当前计数（含日期）"""
    _roll()
    return dict(_data), _day


def reset():
    global _data
    _roll()
    _data = {k: 0 for k in COUNTERS}


def describe():
    """给 !stats 用的一行行文本"""
    data, day = snapshot()
    labels = {
        "replies": "回复",
        "images": "配图",
        "voices": "语音",
        "group_answer": "群里接话",
        "group_skip": "群里跳过",
        "proactive": "主动",
        "digest": "浓缩",
    }
    lines = [f"📊 今日统计（{day}）"]
    for k in COUNTERS:
        lines.append(f"  {labels.get(k, k):6} {data.get(k, 0)}")
    total_group = data.get("group_answer", 0) + data.get("group_skip", 0)
    if total_group:
        rate = data.get("group_answer", 0) / total_group
        lines.append(f"  群接话率 {rate:.0%}（{data['group_answer']}/{total_group}）")
    if data.get("replies"):
        img_rate = data.get("images", 0) / data["replies"]
        lines.append(f"  配图率 {img_rate:.0%}（{data.get('images', 0)}/{data['replies']}）")
    return "\n".join(lines)
