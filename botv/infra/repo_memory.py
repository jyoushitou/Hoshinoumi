# ===================== 记忆仓储 =====================
# 对话记忆 / 全局关键词 / 事件记忆
# 迁移自 db.py（v5-R6），SQL 逐字未改

from collections import deque

from ..config import MAX_USER_ROUND, MAX_GLOBAL_KEY
from .conn import get_cursor


# ===================== 对话记忆 =====================

def load_user_memories_from_db():
    """从数据库加载所有用户的对话记忆"""
    c = get_cursor()
    c.execute("SELECT target_id,user_msg,bot_msg FROM user_memory ORDER BY target_id,id")
    pool = {}
    for r in c.fetchall():
        tid = r["target_id"]
        if tid not in pool:
            pool[tid] = deque(maxlen=MAX_USER_ROUND)  # 每个用户最多保留MAX_USER_ROUND轮对话
        pool[tid].append([r["user_msg"], r["bot_msg"]])
    return pool


def add_user_memory_to_db(tid, user_msg, bot_msg):
    """添加一条对话记忆到数据库，并清理超出轮数的旧记录"""
    c = get_cursor()
    c.execute("INSERT INTO user_memory(target_id,user_msg,bot_msg)VALUES(%s,%s,%s)", (tid, user_msg, bot_msg))
    # 删除超出MAX_USER_ROUND的旧记录
    c.execute("DELETE FROM user_memory WHERE id NOT IN(SELECT id FROM(SELECT id FROM user_memory WHERE target_id=%s ORDER BY id DESC LIMIT %s)AS tmp)AND target_id=%s", (tid, MAX_USER_ROUND, tid))
    c.connection.commit()


# ===================== 全局关键词 =====================

def load_global_keywords_from_db():
    """从数据库加载全局关键词集合"""
    c = get_cursor()
    c.execute("SELECT keyword FROM global_keywords ORDER BY id")
    return set(r["keyword"] for r in c.fetchall())


def add_global_keywords_to_db(kws):
    """添加关键词到全局关键词表，超出MAX_GLOBAL_KEY时删除最旧的"""
    c = get_cursor()
    for kw in kws:
        c.execute("INSERT IGNORE INTO global_keywords(keyword)VALUES(%s)", (kw,))  # 忽略重复
    c.execute("SELECT COUNT(*)as cnt FROM global_keywords")
    if c.fetchone()["cnt"] > MAX_GLOBAL_KEY:
        # 只保留最新的MAX_GLOBAL_KEY个
        c.execute("DELETE FROM global_keywords WHERE id NOT IN(SELECT id FROM(SELECT id FROM global_keywords ORDER BY id DESC LIMIT %s)AS tmp)", (MAX_GLOBAL_KEY,))
    c.connection.commit()


# ===================== 事件记忆 =====================

def load_events_from_db(tid, tag_keywords=None, limit=5):
    """加载事件记忆，可按标签关键词过滤（最多3个标签）"""
    c = get_cursor()
    if tag_keywords:
        conds = " OR ".join(["tags LIKE %s" for _ in tag_keywords[:3]])  # 动态构建LIKE条件
        params = [f"%{kw}%" for kw in tag_keywords[:3]]
        sql = f"SELECT event_summary, tags FROM events WHERE target_id=%s AND ({conds}) ORDER BY id DESC LIMIT %s"
        c.execute(sql, [tid] + params + [limit])
    else:
        c.execute("SELECT event_summary, tags FROM events WHERE target_id=%s ORDER BY id DESC LIMIT %s", (tid, limit))
    return [(r["event_summary"], r["tags"]) for r in c.fetchall()]


def add_event_to_db(tid, event_summary, tags=""):
    """添加事件记忆，每个对象最多保留20条"""
    if not event_summary:
        return
    c = get_cursor()
    c.execute("INSERT INTO events(target_id, event_summary, tags) VALUES(%s,%s,%s)", (tid, event_summary, tags))
    # 每个对象最多保留 20 条事件
    c.execute("DELETE FROM events WHERE id NOT IN(SELECT id FROM(SELECT id FROM events WHERE target_id=%s ORDER BY id DESC LIMIT 20)AS tmp)AND target_id=%s", (tid, tid))
    c.connection.commit()
