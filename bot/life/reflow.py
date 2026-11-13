# ===================== 日记回流（v9-U11） =====================
# 昨晚的日记，第二天变成她的记忆和一点点心情。
#
# 规则：
#   - 压成 2~3 条记忆，归到 __self__ 名下（她自己的记忆）
#   - 情绪影响很小：-0.15 ~ +0.15，而且会随当天时间衰减，不累积

import re

from ..log import log_system

MAX_MEMORIES = 3
MIN_MEMORIES = 2
MOOD_CAP = 0.15

# 极简情感词表：够用就行，不引第三方库
NEG_WORDS = ["累", "烦", "难过", "空", "走神", "不想", "疼", "吵", "焦虑", "失眠",
             "冷", "错", "麻烦", "没意思", "算了", "忘", "丢", "迟到", "疼"]
POS_WORDS = ["好", "开心", "顺利", "喜欢", "笑", "暖", "终于", "舒服", "安静", "不错",
             "做了", "吃到", "成功", "完成"]

_SENT_SPLIT = re.compile(r"[。！？!?\n]+")


def split_memories(text, max_n=MAX_MEMORIES):
    """把日记拆成 2~3 条短记忆

    优先取靠前的完整句子（日记通常是「今天…」开头，信息密度最高）。
    """
    text = (text or "").strip()
    if not text:
        return []
    sentences = [s.strip() for s in _SENT_SPLIT.split(text)]
    picked = []
    for s in sentences:
        s = s.strip("，,、 ")
        if len(s) < 6:            # 太短（"嗯""算了"）不成记忆
            continue
        if s.startswith("（") and "纪要" in s:  # 降级时的事件纪要不要
            continue
        if len(s) > 60:           # 太长就截到 60 字
            s = s[:59] + "…"
        picked.append(s)
        if len(picked) >= max_n:
            break
    if len(picked) == 1 and len(sentences) > 1:  # 只有一条时尽量补到两条
        for s in sentences[1:]:
            s = s.strip()
            if 6 <= len(s) <= 60:
                picked.append(s)
                break
    return picked


def sentiment_bias(text):
    """从日记里估一个很小的情绪偏移（-0.15 ~ +0.15）"""
    text = text or ""
    neg = sum(text.count(w) for w in NEG_WORDS)
    pos = sum(text.count(w) for w in POS_WORDS)
    if neg == pos:
        return 0.0
    raw = (pos - neg) * 0.04
    return max(-MOOD_CAP, min(MOOD_CAP, raw))


def reflow(date_str, diary_text):
    """把一篇日记变成记忆 + 情绪偏移，返回 (条数, 偏移)"""
    from ..infra.repo_memory import add_event_to_db, STATE_TARGET

    items = split_memories(diary_text)
    if len(items) < MIN_MEMORIES and diary_text.strip():
        # 凑不够就整段截断当一条，别丢
        items = items or [diary_text.strip()[:60]]

    added = 0
    for text in items:
        try:
            add_event_to_db(STATE_TARGET, text, tags="日记", kind="life", importance=3)
            added += 1
        except Exception as e:
            log_system(f"日记回流写入失败: {e}")
            break

    bias = sentiment_bias(diary_text)
    if bias:
        _apply_bias(bias)

    log_system(f"日记回流({date_str}): {added} 条记忆, 情绪偏移 {bias:+.2f}")
    return added, bias


def _apply_bias(bias):
    """把情绪偏移叠到她当前的状态上（tick 时会逐渐衰减）"""
    try:
        from .state import current
        from ..core import state as cfg
        s = dict(current())
        s["diary_bias"] = max(-MOOD_CAP, min(MOOD_CAP, float(s.get("diary_bias", 0.0)) + bias))
        cfg.bot_state = s
    except Exception:
        pass
