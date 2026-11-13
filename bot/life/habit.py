# ===================== 学口头禅（v12-A17） =====================
# 他老说的那几个词，慢慢会变成她嘴里的词。
#
# 做法：统计他消息里反复出现的 2~4 字片段，够次数才算「口头禅」。
# 不做语义分析，纯频次——简单、可解释、不会瞎学。

import json
import re
from collections import Counter

MIN_LEN = 2
MAX_LEN = 4
MIN_COUNT = 3          # 至少出现 3 次才算
TOP_N = 3              # 最多学 3 个

# 不该学的：语气词、常见连接词、脏话（学了会很难听）
STOP = {
    "就是", "这个", "那个", "什么", "怎么", "可以", "现在", "今天", "明天",
    "但是", "因为", "所以", "然后", "而且", "还是", "已经", "一下", "知道",
    "不是", "没有", "我们", "你们", "他们", "自己", "时候", "这样", "那样",
    "真的", "感觉", "应该", "可能", "觉得", "哈哈", "呵呵", "嗯嗯", "啊啊",
}

_CLEAN = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]+")


def _chunks(text):
    """按标点切成小段，只在段内找重复，避免跨句拼出怪词"""
    text = (text or "").strip()
    if not text:
        return []
    parts = _CLEAN.split(text)
    return [p for p in parts if len(p) >= MIN_LEN]


def _segment(chunk):
    """切词：优先 jieba，拿不到词性时退回单字（只在测试环境会发生）"""
    try:
        import jieba
        words = [w.strip() for w in jieba.lcut(chunk)]
        if any(len(w) >= MIN_LEN for w in words):
            return words
    except Exception:
        pass
    return list(chunk)


def ngrams(text):
    """候选片段：优先整词（2~4 字），再补相邻两词的组合

    只按字符切会跨词边界，学出「绝了这」这种废词——所以先分词。
    """
    out = []
    for chunk in _chunks(text):
        words = [w for w in _segment(chunk) if w]
        for word in words:
            if MIN_LEN <= len(word) <= MAX_LEN and word not in STOP:
                out.append(word)
        # 相邻两词拼起来也算（「太」「离谱」→「太离谱」）
        for a, b in zip(words, words[1:]):
            piece = a + b
            if MIN_LEN <= len(piece) <= MAX_LEN and piece not in STOP:
                out.append(piece)
    return out


def update(counter, text):
    """把一句话里的候选片段累加到 counter（调用方负责持久化）"""
    for piece in ngrams(text):
        counter[piece] += 1
    return counter


def top(counter, n=TOP_N):
    """挑出够次数、且没被更长片段包含的口头禅"""
    if not counter:
        return []
    candidates = [(w, c) for w, c in counter.items() if c >= MIN_COUNT]
    candidates.sort(key=lambda kv: (-kv[1], -len(kv[0])))

    # 次数相同时优先短词（「绝了」胜过「绝了这」）
    candidates.sort(key=lambda kv: (-kv[1], len(kv[0])))
    picked = []
    for word, _count in candidates:
        # 和已选的互相包含就跳过，避免「绝了」和「绝了这」同时存在
        if any(word in p or p in word for p in picked):
            continue
        picked.append(word)
        if len(picked) >= n:
            break
    return picked


def describe(phrases):
    """给 prompt 用的一句话"""
    if not phrases:
        return ""
    return "他最近老说：" + "、".join(phrases)


# ===================== 存取与训练 =====================

def load(tid):
    """从库里读回计数（读不到就空）"""
    from ..core import state as cfg
    tid = str(tid)
    if tid in cfg.habit_counters:
        return cfg.habit_counters[tid]
    counter = Counter()
    try:
        from ..infra.repo_memory import load_habit
        raw = load_habit(tid)
        if raw:
            counter.update(json.loads(raw))
    except Exception:
        pass
    cfg.habit_counters[tid] = counter
    return counter


def save(tid):
    """把计数存回去（失败不影响回复）"""
    from ..core import state as cfg
    tid = str(tid)
    counter = cfg.habit_counters.get(tid)
    if not counter:
        return False
    try:
        from ..infra.repo_memory import save_habit
        data = {w: c for w, c in counter.items() if c >= 2}
        save_habit(tid, json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        return True
    except Exception:
        return False


def learn(tid, text):
    """收到一条消息：学一点，够 10 次最多的一批就落库一次"""
    counter = load(tid)
    update(counter, text)
    if sum(counter.values()) % 10 == 0:
        save(tid)
    return counter


def phrases_for(tid):
    """给 prompt 用：这个人的口头禅"""
    try:
        return top(load(tid))
    except Exception:
        return []
