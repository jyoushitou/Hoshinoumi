# ===================== 元数据（v18.5，修 L6） =====================
# 为什么不用 logs 表：log 有 180 天 TTL，清空后「首次日志」就没了，
# uptime 会归零。启动时间属于「机器人自己的元数据」，单独存。

from ..log import log_api


def set_value(k, v, cursor=None):
    """写一条元数据（存在就更新）"""
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        try:
            c.execute(
                "INSERT INTO bot_meta(k, v) VALUES(%s, %s) "
                "ON DUPLICATE KEY UPDATE v=VALUES(v)", (k, str(v)))
        except Exception:
            # SQLite 不支持 ON DUPLICATE KEY
            c.execute(
                "INSERT OR REPLACE INTO bot_meta(k, v) VALUES(%s, %s)",
                (k, str(v)))
        c.connection.commit()
        return True
    except Exception as e:
        log_api(f"[元数据] 写入失败（{k}）：{e}")
        return False
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def get_value(k, default=None, cursor=None):
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute("SELECT v FROM bot_meta WHERE k=%s", (k,))
        row = c.fetchone()
        if not row:
            return default
        return row["v"] if isinstance(row, dict) else row[0]
    except Exception:
        return default
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def mark_start(version=""):
    """启动时调一次：首次启动时间只在第一次写，之后不动"""
    from ..core import clock

    first = get_value("first_start")
    if not first:
        set_value("first_start", clock.fmt_full())
    if version:
        set_value("version", version)
    return get_value("first_start")


def uptime_text(cursor=None):
    """给 !uptime 用：「N 天 H 小时 M 分钟」；读不到返回空"""
    from ..core import clock

    raw = get_value("first_start", cursor=cursor)
    if not raw:
        return ""
    start = clock.parse(str(raw)[:19])
    if not start:
        return ""
    delta = clock.naive() - start
    if delta.total_seconds() < 0:
        return ""
    days = delta.days
    hours = delta.seconds // 3600
    mins = (delta.seconds % 3600) // 60
    return f"{days}天{hours}小时{mins}分钟", start


def describe(cursor=None):
    """!meta 用：把 bot_meta 全列出来"""
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        c.execute("SELECT k, v, updated_at FROM bot_meta ORDER BY k")
        rows = list(c.fetchall())
        if not rows:
            return "📋 暂无元数据"
        lines = ["📋 机器人元数据："]
        for r in rows:
            lines.append(f"  {r['k']}: {r['v']}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 读取元数据失败: {e}"
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass
