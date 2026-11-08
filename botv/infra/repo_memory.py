# ===================== 记忆仓储 =====================
# 对话记忆 / 全局关键词 / 事件记忆
# 迁移自 db.py（v5-R6），SQL 逐字未改

from collections import deque
from datetime import datetime, timedelta

from ..config import MAX_USER_ROUND, MAX_GLOBAL_KEY, CST
from .conn import get_cursor
from .dedupe import dedupe_key

# v7-B15：去重窗口与按 kind 的保留上限
DEDUPE_WINDOW_DAYS = 7
KIND_LIMITS = {"life": 60, "event": 30, "promise": 30, "profile": 20}
KIND_LIMIT_DEFAULT = 20
# 旧代码调 load_events_from_db 时默认只看这几类
DEFAULT_KINDS = ("event", "life", "promise")


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

def load_events_from_db(tid, tag_keywords=None, limit=5, kinds=None):
    """加载记忆，可按标签或 kind 过滤（默认排除 profile）

    v7-B8：多了 kind 维度；旧数据 kind 默认 'event'，兼容。
    """
    c = get_cursor()
    kinds = tuple(kinds) if kinds is not None else DEFAULT_KINDS
    kind_ph = ",".join(["%s"] * len(kinds))
    params = [tid] + list(kinds)

    if tag_keywords:
        conds = " OR ".join(["tags LIKE %s" for _ in tag_keywords[:3]])  # 动态构建LIKE条件
        sql = (f"SELECT event_summary, tags FROM events "
               f"WHERE target_id=%s AND kind IN ({kind_ph}) AND ({conds}) "
               f"ORDER BY id DESC LIMIT %s")
        c.execute(sql, params + [f"%{kw}%" for kw in tag_keywords[:3]] + [limit])
    else:
        sql = (f"SELECT event_summary, tags FROM events "
               f"WHERE target_id=%s AND kind IN ({kind_ph}) "
               f"ORDER BY id DESC LIMIT %s")
        c.execute(sql, params + [limit])
    return [(r["event_summary"], r["tags"]) for r in c.fetchall()]


def load_timeline(tid, days=7, limit=12):
    """最近 N 天的记忆，按时间倒序（v8-B16）"""
    c = get_cursor()
    c.execute("""
        SELECT DATE(COALESCE(last_seen, created_at)) AS day,
               event_summary AS summary
        FROM events
        WHERE target_id=%s AND kind IN ('event', 'life')
          AND COALESCE(last_seen, created_at) >= NOW() - INTERVAL %s DAY
        ORDER BY COALESCE(last_seen, created_at) DESC
        LIMIT %s
    """, (tid, days, limit))
    return list(c.fetchall())


def load_memories_for_search(tid, limit=300):
    """取一批候选记忆喂给检索器（v8-B11）"""
    c = get_cursor()
    c.execute("""
        SELECT id, kind, event_summary AS summary, tags, importance, hit_count,
               created_at, last_seen
        FROM events
        WHERE target_id=%s AND kind IN ('event','life','promise')
        ORDER BY id DESC LIMIT %s
    """, (tid, limit))
    return list(c.fetchall())


def add_event_to_db(tid, event_summary, tags="", kind="event", importance=3, due_date=None):
    """写入一条记忆（v7-B15）

    - 7 天窗口内命中同一 dedupe_key → 只累加 hit_count、更新 last_seen
    - 否则插入新行，并按 kind 的上限裁剪最旧的
    """
    if not event_summary:
        return None
    c = get_cursor()
    key = dedupe_key(tid, kind, event_summary)
    now = datetime.now(CST)

    c.execute("""
        SELECT id FROM events
        WHERE target_id=%s AND kind=%s AND dedupe_key=%s
          AND COALESCE(last_seen, created_at) >= %s
        ORDER BY id LIMIT 1
    """, (tid, kind, key, now - timedelta(days=DEDUPE_WINDOW_DAYS)))
    hit = c.fetchone()
    if hit:  # 命中：不新增，只记账
        c.execute("UPDATE events SET hit_count=hit_count+1, last_seen=%s WHERE id=%s", (now, hit["id"]))
        c.connection.commit()
        return hit["id"]

    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, importance, due_date, last_seen) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (tid, event_summary, tags, kind, key, importance, due_date, now),
    )
    # 按 kind 分别保留
    keep = KIND_LIMITS.get(kind, KIND_LIMIT_DEFAULT)
    c.execute(
        "DELETE FROM events WHERE id NOT IN("
        "SELECT id FROM(SELECT id FROM events WHERE target_id=%s AND kind=%s ORDER BY id DESC LIMIT %s)AS tmp"
        ")AND target_id=%s AND kind=%s",
        (tid, kind, keep, tid, kind),
    )
    c.connection.commit()
    return None
