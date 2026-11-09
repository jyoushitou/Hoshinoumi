# ===================== 提示词分层预算（v8-B13） =====================
# 中文里 1 个字大致 0.6~1 个 token，这里按「字数」做预算，保守一点。
# 超预算就从最不重要的一层开始砍：检索记忆 → 对话历史 → 画像 → 人设（人设不砍）。

BUDGET = {
    "profile": 120,     # 画像：一行就够
    "dialogue": 700,    # 最近对话（v14.1：轮数延长到 30，预算跟着涨）
    "memories": 250,    # 检索到的记忆
    "keywords": 120,    # 全局关键词
    "timeline": 200,    # 最近 7 天时间线
}
TOTAL = 1800  # 这几层加起来的上限（不含人设与标签表）


def trim(text, limit):
    """超长截断，加省略号"""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def cap_lines(lines, limit):
    """从最近的一条往前取，直到用完预算

    lines 按「时间正序」传入（旧的在前）。返回 (文本, 实际用到多少字)
    """
    kept = []
    used = 0
    for line in reversed(list(lines)):
        cost = len(line) + (1 if kept else 0)  # 换行符
        if kept and used + cost > limit:
            break
        kept.append(line)
        used += cost
    kept.reverse()
    return "\n".join(kept), used


def report(**parts):
    """给日志用的一行预算报告"""
    items = " ".join(f"{k}={len(v or '')}" for k, v in parts.items())
    total = sum(len(v or "") for v in parts.values())
    flag = "⚠️" if total > TOTAL else "✅"
    return f"{flag} {items} total={total}/{TOTAL}"
