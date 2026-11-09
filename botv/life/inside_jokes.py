# ===================== 内部梗（v12-G37） =====================
# 你们之间反复出现的东西，慢慢就成了「梗」。
#
# 做法：统计记忆标签，出现 ≥3 次的算「你们常提的事」。
# 不做语义判断——只认频次，宁可漏也不瞎编。

from collections import Counter

MIN_COUNT = 3
MAX_JOKES = 3


def count_tags(memories):
    """从记忆行里统计标签频次"""
    counter = Counter()
    for row in memories or []:
        tags = (row.get("tags") or "") if isinstance(row, dict) else ""
        for tag in tags.replace("，", ",").split(","):
            tag = tag.strip()
            if tag:  # 中文单字（猫/雨/琴）也算，噪声靠频次过滤
                counter[tag] += 1
    return counter


def pick_jokes(counter, limit=MAX_JOKES):
    """够次数、按频次排序，取前几个"""
    if not counter:
        return []
    picked = [w for w, c in counter.most_common(50) if c >= MIN_COUNT]
    return picked[:limit]


def describe(jokes):
    """给 prompt 用的一句话"""
    if not jokes:
        return ""
    return "你们常提：" + "、".join(jokes)


def top_jokes(tid, limit=MAX_JOKES):
    """读这个人的记忆，挑出内部梗"""
    try:
        from ..infra.repo_memory import load_memories_for_search
        rows = load_memories_for_search(str(tid), limit=300)
    except Exception:
        return []
    return pick_jokes(count_tags(rows), limit)
