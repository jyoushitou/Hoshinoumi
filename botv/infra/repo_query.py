# ===================== 只读查询仓库（v17.16 债三） =====================
# 命令层和 HTTP 层都不该写 SQL。这里集中放「统计/计数/最近记录」这类只读查询，
# 返回纯 dict，方便命令层格式化、也方便测试。
#
# 纪律：
#   - 只读，不带业务判断
#   - 表不存在/查询失败 → 返回 0 或空，不抛（统计接口不该拖垮命令）

from ..log import log_api

_TABLES = ("images", "user_memory", "events", "logs", "global_keywords",
           "ai_raw_responses", "memories", "bot_states", "relations",
           "habits", "reading_progress", "cron_tasks")


def count_table(table, cursor=None):
    """单表行数；表不存在返回 0"""
    if table not in _TABLES:
        raise ValueError(f"不允许统计表：{table}")
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        row = c.fetchone()
        return int(list(row.values())[0] or 0)
    except Exception:
        return 0
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def counts(tables=None, cursor=None):
    """多表计数：{表名: 行数}；v18.13 传游标不缓存，否则 5 秒 TTL"""
    names = list(tables or _TABLES)
    if cursor is not None:  # 调用方要一致性快照，别给缓存
        return {t: count_table(t, cursor) for t in names}
    from . import cache
    key = "counts:" + ",".join(names)
    hit = cache.get(key)
    if hit is not None:
        return dict(hit)
    val = {t: count_table(t) for t in names}
    cache.set(key, val, ttl=5.0)
    return val


def first_log(cursor=None):
    """最早一条日志的时间（用于 uptime 之类）"""
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute("SELECT MIN(id) AS first_id, MIN(created_at) AS first_log FROM logs")
        row = c.fetchone() or {}
        return {"first_id": row.get("first_id"), "first_log": row.get("first_log")}
    except Exception:
        return {"first_id": None, "first_log": None}
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def recent_logs(limit=20, cursor=None):
    """最近日志（!log 用）"""
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute("SELECT level, message, created_at FROM logs "
                  "ORDER BY id DESC LIMIT %s", (int(limit),))
        return list(c.fetchall())
    except Exception as e:
        log_api(f"[查询] 读日志失败：{e}")
        return []
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def clear_target(target, cursor=None):
    """清掉某个对象在旧表里的记忆（!clear 用）"""
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute("DELETE FROM user_memory WHERE target_id=%s", (str(target),))
        c.execute("DELETE FROM events WHERE target_id=%s", (str(target),))
        c.connection.commit()
        return True
    except Exception as e:
        log_api(f"[查询] 清记忆失败：{e}")
        return False
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def describe(cursor=None):
    """给 !db 命令用的摘要"""
    data = counts(("images", "user_memory", "events", "logs",
                   "global_keywords", "ai_raw_responses"), cursor)
    first = first_log(cursor)
    return {"counts": data, "first": first}
