# ===================== 对话记忆上下文（v8 拆包） =====================
# 管理用户对话记忆、全局关键词、事件记忆的存储和检索

import jieba  # 中文分词库
from collections import deque  # 双端队列（用于对话记忆池）

from ..config import MAX_USER_ROUND  # 每个用户最大对话轮数
from ..infra.repo_memory import load_user_memories_from_db, load_global_keywords_from_db, add_user_memory_to_db, add_global_keywords_to_db, load_events_from_db, add_event_to_db  # 数据库操作
from ..log import log_system  # 日志
from botv.core import state as cfg  # 全局运行时变量


from .text import extract_keywords  # noqa: E402  分词工具（v8 挪出去避免循环导入）
from .retrieval import retrieve  # noqa: E402  双路召回（v8-B11）
from .inject import BUDGET, trim, cap_lines  # noqa: E402  分层预算（v8-B13）
from ..infra.repo_memory import load_memories_for_search, load_keywords_from_db  # noqa: E402


def load_memories():
    """从数据库加载对话记忆和关键词（v8-B12：关键词按对象分开）"""
    cfg.user_memory_pool = load_user_memories_from_db()  # 对话记忆池
    kw_map = load_keywords_from_db()  # {target_id: set}
    cfg.global_keyword_set = kw_map.get("", set())  # 公共词库
    cfg.target_keyword_sets = {k: v for k, v in kw_map.items() if k}  # 每个人自己的词
    log_system(f"记忆: {len(cfg.user_memory_pool)}对象,"
               f"公共词{len(cfg.global_keyword_set)},分对象词{len(cfg.target_keyword_sets)}组")




def add_target_memory(tid, user_msg, bot_msg, img_keywords=None, refined_keywords=None, event_summary=None):
    """添加一条对话记忆：入库+内存更新+事件存储+关键词更新

    v5-F2：兜底文案（Fallback）一律不入库——它是系统噪声，不是她说的话。
    """
    from ..core.types import Fallback
    if isinstance(bot_msg, Fallback):
        log_system(f"记忆: 跳过兜底文案，不入库 (tid={tid})")
        return
    add_user_memory_to_db(tid, user_msg, bot_msg)  # 写入数据库
    pool = cfg.user_memory_pool.setdefault(tid, deque(maxlen=MAX_USER_ROUND))
    if len(pool) >= MAX_USER_ROUND:  # v14.1-D3：满了就把最旧一轮挪进待浓缩缓冲
        try:
            old = pool.popleft()
            buf = cfg.digest_pending.setdefault(tid, [])
            buf.append(old)
            if len(buf) > 100:  # 防止无限堆积
                del buf[:50]
        except Exception:
            pass
    pool.append([user_msg, bot_msg])  # 更新内存池
    
    # 存储事件（带标签）
    if event_summary:  # 有事件摘要
        tag_str = ",".join(refined_keywords[:5]) if refined_keywords else ""  # 取前5个提炼关键词作为标签
        add_event_to_db(tid, event_summary, tag_str)  # 写入数据库
    
    # AI提炼的关键词合并到长期记忆（v8-B12：写到这个对象名下）
    if refined_keywords:
        add_global_keywords_to_db(refined_keywords, tid)
        cfg.target_keyword_sets.setdefault(tid, set()).update(refined_keywords)
    else:
        nk = extract_keywords(f"{user_msg} {bot_msg}")
        if img_keywords:
            nk.extend(img_keywords)
        add_global_keywords_to_db(nk, tid)
        cfg.target_keyword_sets.setdefault(tid, set()).update(nk)


def build_memory_context(tid, current_kws=None, query=None):
    """构建对话上下文：全局关键词 + 最近对话 + 检索到的相关记忆

    v8-B11：记忆不再用 LIKE 硬匹配，改为 BM25 + 关键词双路召回。
    v8-B13：每层按预算裁剪，总长可控。
    """
    words = set(cfg.target_keyword_sets.get(tid, set())) | set(cfg.global_keyword_set)  # 这个人的词 + 公共词
    kw = "、".join(sorted(words)) if words else "无"  # 顿号分隔

    rounds = []
    if tid in cfg.user_memory_pool:  # 该用户有记忆
        for u, b in list(cfg.user_memory_pool[tid])[-30:]:  # v14.1：最多取 30 轮，按预算再砍
            rounds.append(f"用户:{u}\n奈绪:{b}")
    dia, _ = cap_lines(rounds, BUDGET["dialogue"]) if rounds else ("无", 0)

    q = query or " ".join(current_kws or [])  # 检索用的查询串
    events_str = _recall_memories(tid, q)  # 双路召回

    kw = trim(kw, BUDGET["keywords"])
    events_str = trim(events_str, BUDGET["memories"])
    return kw, dia, events_str  # 返回(全局关键词, 对话历史, 相关记忆)


def _recall_memories(tid, query, top_k=5):
    """检索相关记忆；检索不到就退回最近几条，绝不给空"""
    cands = []
    try:
        cands = load_memories_for_search(tid, limit=300)
    except Exception:
        cands = []

    if cands and query:
        try:
            hits = retrieve(query, cands, top_k=top_k)
        except Exception:
            hits = []
        if hits:
            return "\n".join(f"· {m.get('summary', '')}" for m, _ in hits)

    # 兜底：最近几条（老逻辑）
    try:
        recent = load_events_from_db(tid, tag_keywords=None, limit=3)
        return "\n".join(f"· {e[0]}" for e in recent) if recent else "无"
    except Exception:
        return "无"

