# ===================== 元数据（v18.5，修 L6） =====================
# 为什么不用 logs 表：log 有 180 天 TTL，清空后「首次日志」就没了，
# uptime 会归零。启动时间属于「机器人自己的元数据」，单独存 bot_meta。
#
# 两个关键设计：
#   1. 读一律走 v_bot_meta 视图（U2：查询只认视图），应用层不再各写一套 SQL；
#   2. 视图用 epoch 相减（first_start_ts），不用库的 NOW()——
#      MySQL 服务器时区常是 UTC，字符串相减会又差 8 小时（L11 同源）。

from ..log import log_api


def _backend():
    """当前后端：mysql / sqlite（按游标来源判断，不靠异常猜）"""
    try:
        from .conn import _resolve_backend

        return _resolve_backend()
    except Exception:
        return "mysql"


def _get_cursor(cursor):
    """拿游标；返回 (cursor, 是否需要自己关)"""
    if cursor is not None:
        return cursor, False
    from .conn import get_cursor

    return get_cursor(), True


def _close(c):
    try:
        c.close()
    except Exception:
        pass


def _upsert(c, k, v):
    """存在就更新：两种方言各写一句，不靠 try/except 猜"""
    if _backend() == "sqlite":
        c.execute(
            "INSERT INTO bot_meta(k, v, updated_at) "
            "VALUES(%s, %s, datetime('now','localtime')) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v, "
            "updated_at=excluded.updated_at",
            (k, str(v)))
    else:
        c.execute(
            "INSERT INTO bot_meta(k, v) VALUES(%s, %s) "
            "ON DUPLICATE KEY UPDATE v=VALUES(v), updated_at=CURRENT_TIMESTAMP",
            (k, str(v)))


def _insert_once(c, k, v):
    """只在不存时插入：启动时间用，两个进程同时启动也不会互相覆盖"""
    if _backend() == "sqlite":
        # updated_at 也显式给本地时间：SQLite 的 CURRENT_TIMESTAMP 是 UTC（L11 同源）
        c.execute("INSERT OR IGNORE INTO bot_meta(k, v, updated_at) "
                  "VALUES(%s, %s, datetime('now','localtime'))",
                  (k, str(v)))
    else:
        c.execute("INSERT IGNORE INTO bot_meta(k, v) VALUES(%s, %s)",
                  (k, str(v)))


def set_value(k, v, cursor=None):
    """写一条元数据（存在就更新）"""
    c, owned = _get_cursor(cursor)
    try:
        _upsert(c, k, v)
        c.connection.commit()
        return True
    except Exception as e:
        log_api(f"[元数据] 写入失败（{k}）：{e}")
        return False
    finally:
        if owned:
            _close(c)


def get_value(k, default=None, cursor=None):
    """读一条元数据（不做视图派生，只给内部兜底用）"""
    c, owned = _get_cursor(cursor)
    try:
        c.execute("SELECT v FROM bot_meta WHERE k=%s", (k,))
        row = c.fetchone()
        if not row:
            return default
        return row["v"] if isinstance(row, dict) else row[0]
    except Exception:
        return default
    finally:
        if owned:
            _close(c)


def _seconds_since(raw):
    """字符串启动时间 → 已运行秒数（按北京时间解析，与应用时钟同源）"""
    from ..core import clock

    start = clock.parse(str(raw)[:19])
    if not start:
        return None
    return int((clock.naive() - start).total_seconds())


def _human(secs):
    """秒 → 「N 天 H 小时 M 分钟」"""
    secs = max(0, int(secs))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    return f"{days}天{hours}小时{rem // 60}分钟"


def mark_start(version=""):
    """启动时调一次：首次启动时间只写一次，之后不动；版本每次刷新"""
    from ..core import clock

    c, owned = _get_cursor(None)
    try:
        now = clock.now()
        first = get_value("first_start", cursor=c)
        if not first:
            _insert_once(c, "first_start", clock.fmt_full(now))
            _insert_once(c, "first_start_ts", int(now.timestamp()))
            first = get_value("first_start", cursor=c)
        elif not get_value("first_start_ts", cursor=c):
            # 老库只有字符串：补一份 epoch，视图才有得算
            start = clock.parse(str(first)[:19])
            if start:
                _insert_once(c, "first_start_ts",
                             int(clock.to_cst(start).timestamp()))
        if version:
            _upsert(c, "version", version)
        c.connection.commit()
        return first or ""
    except Exception as e:
        log_api(f"[元数据] 记录启动失败：{e}")
        return ""
    finally:
        if owned:
            _close(c)


def uptime_row(cursor=None):
    """读 v_bot_meta 视图（U2：查询只认视图）；视图没建出来时返回 None"""
    c, owned = _get_cursor(cursor)
    try:
        c.execute("SELECT first_start, first_start_ts, version, "
                  "uptime_seconds, days_since FROM v_bot_meta")
        row = c.fetchone()
        if not row:
            return None
        return dict(row)
    except Exception:
        return None
    finally:
        if owned:
            _close(c)


def _pack(first_start, version, secs, source):
    from ..core import clock

    secs = max(0, int(secs))
    return {
        "first_start": str(first_start)[:19],
        "version": version or "",
        "uptime_seconds": secs,
        "days_since": secs // 86400,
        "uptime_text": _human(secs),
        "start": clock.parse(str(first_start)[:19]),
        "source": source,
    }


def uptime(cursor=None):
    """运行时长（视图优先，表兜底）

    返回 dict：first_start / version / uptime_seconds / days_since /
              uptime_text / start / source；读不到返回 None
    """
    row = uptime_row(cursor)
    if row and row.get("first_start"):
        secs = row.get("uptime_seconds")
        if secs is None:
            # 视图在、但缺 first_start_ts（老库）：应用侧按字符串算
            secs = _seconds_since(row["first_start"])
            source = "table"
        else:
            source = "view"
        if secs is not None:
            return _pack(row["first_start"], row.get("version"), secs, source)

    # 视图查询失败 / 还没建：退回表里算（!uptime 不能因为视图挂掉就不可用）
    raw = get_value("first_start", cursor=cursor)
    if not raw:
        return None
    secs = _seconds_since(raw)
    if secs is None:
        return None
    return _pack(raw, get_value("version", cursor=cursor), secs, "table")


def uptime_text(cursor=None):
    """兼容旧调用：返回 (人话, 首次启动 datetime)；读不到返回空串"""
    info = uptime(cursor)
    if not info:
        return ""
    return info["uptime_text"], info["start"]


def describe(cursor=None):
    """!meta 用：元数据视图 + 表内键值"""
    info = uptime(cursor)
    lines = ["📋 机器人元数据："]
    if info:
        lines.append(f"  首次启动: {info['first_start']}")
        lines.append(f"  已运行: {info['uptime_text']}（第 {info['days_since'] + 1} 天）")
        lines.append(f"  当前版本: {info['version'] or '未知'}")
        lines.append("  数据来源: " + ("v_bot_meta 视图"
                                      if info["source"] == "view"
                                      else "bot_meta 表（视图不可用，已兜底）"))
    else:
        lines.append("  首次启动: 未记录（跑一次启动流程就会写入）")

    c, owned = _get_cursor(cursor)
    try:
        c.execute("SELECT k, v FROM bot_meta ORDER BY k")
        rows = [dict(r) for r in c.fetchall()]
        if rows:
            lines.append("  表内键值：")
            for r in rows:
                lines.append(f"    {r['k']} = {r['v']}")
    except Exception as e:
        lines.append(f"  ❌ 读取元数据失败: {e}")
    finally:
        if owned:
            _close(c)
    return "\n".join(lines)
