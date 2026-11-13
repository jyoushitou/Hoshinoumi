# ===================== 记忆检索（v8-B11/B17） =====================
# 不依赖向量模型：关键词精确匹配 + BM25 模糊匹配，RRF 融合成一路。
# 以后接上 embedding，只要再加一路排名丢进 rrf 就行。

import math
from collections import Counter

import jieba

from .text import extract_keywords


def tokenize(text, cut=None):
    """检索用分词（长度 > 1 的词）；cut 可注入，便于测试"""
    words = (cut or jieba.lcut)(text or "")
    return [w for w in words if len(str(w)) > 1]


class BM25:
    """小型语料的 BM25——几十到几百条记忆足够用"""

    def __init__(self, docs, k1=1.5, b=0.75, tokenizer=None):
        self.k1 = k1
        self.b = b
        _cut = tokenizer or tokenize
        self.tfs = [Counter(_cut(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df = Counter()
        for tf in self.tfs:
            for w in tf:
                df[w] += 1
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(self, terms, i):
        """第 i 篇文档对 terms 的 BM25 得分"""
        if not self.avg or i >= len(self.tfs):
            return 0.0
        tf = self.tfs[i]
        length = self.lens[i]
        s = 0.0
        for w in terms:
            f = tf.get(w)
            if not f:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * length / self.avg)
            s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / denom
        return s


def rrf(rank_lists, k=60):
    """Reciprocal Rank Fusion：把多路排名合成一路

    rank_lists: [[key, key, ...], ...]（key 必须可哈希，一般用下标）
    返回 [(key, score), ...]，按分数降序
    """
    scores = {}
    for lst in rank_lists:
        for rank, item in enumerate(lst, 1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def retrieve(query, memories, top_k=5, tokenizer=None):
    """从候选记忆里挑最相关的 top_k 条

    memories: [{"summary":..., "tags":..., "importance":..., "hit_count":...}, ...]
    返回 [(memory, score), ...]
    """
    if not memories or not query:
        return []
    if tokenizer is not None:
        terms = tokenizer(query)
    else:
        terms = extract_keywords(query)
    if not terms:
        return []

    docs = [f"{m.get('summary', '')} {m.get('tags', '') or ''}" for m in memories]
    bm = BM25(docs, tokenizer=tokenizer)
    bm_scores = [bm.score(terms, i) for i in range(len(docs))]
    bm_rank = sorted(range(len(docs)), key=lambda i: bm_scores[i], reverse=True)

    # 第二路：关键词命中的条数 + 历史热度 + 重要度
    def kw_key(i):
        hits = sum(1 for t in terms if t in docs[i])
        return (hits, memories[i].get("hit_count", 0) or 0, memories[i].get("importance", 0) or 0)

    kw_rank = sorted(range(len(docs)), key=kw_key, reverse=True)

    fused = rrf([bm_rank, kw_rank])

    # v18.2 U3：按记忆分量加权——同等相关时，重的事排前面
    def _boost(item):
        idx, score = item
        try:
            w = float(memories[idx].get("weight", 0.5) or 0.5)
        except Exception:
            w = 0.5
        return score * (0.6 + 0.4 * max(0.0, min(1.0, w)))

    fused = sorted(((i, _boost((i, s))) for i, s in fused),
                   key=lambda x: x[1], reverse=True)

    out = []
    for idx, score in fused[:top_k]:
        if bm_scores[idx] <= 0 and kw_key(idx)[0] == 0:
            continue  # 两路都没命中，不要硬凑
        out.append((memories[idx], round(score, 6)))
    return out
