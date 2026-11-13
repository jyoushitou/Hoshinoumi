# ===================== 短期对话消息仓储（v19.1） =====================
# conversation_messages：每个会话保留最近 1 天 / 100 条。
# 写失败不阻塞聊天；读给 !history / 内部 API。

import json
import logging
from datetime import datetime, timedelta

from .conn import get_cursor, _resolve_backend

log = logging.getLogger("conversation")
MAX_PER_THREAD = 100
RETENTION_DAYS = 1


def _backend():
    try:
        return _resolve_backend()
    except Exception:
        return "sqlite"


def _cursor(cursor=None):
    return cursor or get_cursor()


def append(user_id="__owner__", target_id="", content="", role="user",
           channel="qq", thread_id=None, message_id=None, meta=None,
           cursor=None):
    """写一条消息；同一 channel+message_id 只写一次"""
    content = (content or "").strip()
    if not content or not target_id:
        return False
    c = _cursor(cursor)
    sqlite = _backend() == "sqlite"
    head = "INSERT OR IGNORE" if sqlite else "INSERT IGNORE"
    sql = (f"{head} INTO conversation_messages "
           "(user_id,target_id,thread_id,channel,role,content,message_id,meta) "
           "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)")
    payload = (
        str(user_id or "__owner__"), str(target_id), thread_id,
        str(channel or "qq"), str(role), content,
        str(message_id) if message_id else None,
        json.dumps(meta, ensure_ascii=False) if meta else None,
    )
    try:
        c.execute(sql, payload)
        c.connection.commit()
        return True
    except Exception as e:
        try:
            c.connection.rollback()
        except Exception:
            pass
        log.warning("conversation append failed: %s", e)
        return False


def recent(target_id, limit=20, before_id=None, user_id=None, cursor=None):
    """按 target 取最近消息，返回时间正序；before_id 用于游标分页"""
    limit = max(1, min(int(limit or 20), MAX_PER_THREAD))
    c = _cursor(cursor)
    where = ["target_id=%s"]
    params = [str(target_id)]
    if user_id is not None:
        where.append("user_id=%s")
        params.append(str(user_id))
    if before_id:
        where.append("id < %s")
        params.append(int(before_id))
    sql = ("SELECT id,user_id,target_id,thread_id,channel,role,content,"
           "message_id,meta,created_at FROM conversation_messages WHERE "
           + " AND ".join(where) + " ORDER BY id DESC LIMIT %s")
    params.append(limit)
    c.execute(sql, tuple(params))
    rows = list(c.fetchall() or [])
    return list(reversed(rows))


def cleanup(days=RETENTION_DAYS, max_per_thread=MAX_PER_THREAD, cursor=None):
    """删 1 天前，并把每个 (user_id,target_id) 截到最近 100 条"""
    c = _cursor(cursor)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    deleted = 0
    try:
        c.execute("DELETE FROM conversation_messages WHERE created_at < %s", (cutoff,))
        deleted += int(getattr(c, "rowcount", 0) or 0)
        c.execute("SELECT DISTINCT user_id,target_id FROM conversation_messages")
        groups = list(c.fetchall() or [])
        for g in groups:
            c.execute(
                "SELECT id FROM conversation_messages WHERE user_id=%s AND target_id=%s "
                "ORDER BY id DESC LIMIT %s OFFSET %s",
                (g["user_id"], g["target_id"], max_per_thread, max_per_thread),
            )
            extra = [r["id"] for r in (c.fetchall() or [])]
            if extra:
                marks = ",".join(["%s"] * len(extra))
                c.execute(f"DELETE FROM conversation_messages WHERE id IN ({marks})", tuple(extra))
                deleted += len(extra)
        c.connection.commit()
    except Exception as e:
        try:
            c.connection.rollback()
        except Exception:
            pass
        log.warning("conversation cleanup failed: %s", e)
    return deleted
