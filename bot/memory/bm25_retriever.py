# ===================== BM25Retriever native（v31.2） =====================
# 包装现有 BM25 + 关键词双路召回；检索结果仍返回 [{...,"score":...}]。

from ..infra.repo_memory import load_memories_for_search
from ..memory.retrieval import retrieve


class BM25Retriever:
    name = "bm25"

    async def search(self, user_id, query, top_k=5):
        cands = load_memories_for_search(str(user_id), limit=300, user_id=str(user_id))
        hits = retrieve(query, cands, top_k=int(top_k))
        out = []
        for mem, score in hits:
            row = dict(mem)
            row["score"] = score
            out.append(row)
        return out
