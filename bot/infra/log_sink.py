# ===================== 日志落库/读取（v19.4） =====================
# 独立于 bot.log：log 只负责文件/内存，这里才依赖 DB。
# 这样 log 不再反向 import db/conn，持久层环可以拆掉。

from datetime import datetime

from ..config import CST


def write_log_to_db(level, msg):
    try:
        from .conn import get_cursor

        c = get_cursor()
        c.execute("INSERT INTO logs(level,message,created_at)VALUES(%s,%s,%s)",
                  (level, msg, datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')))
        c.connection.commit()
    except Exception:
        pass


def get_recent_logs(limit=20):
    try:
        from .conn import get_cursor

        c = get_cursor()
        c.execute("SELECT level, message, created_at FROM logs ORDER BY id DESC LIMIT %s",
                  (limit,))
        rows = c.fetchall()
        if not rows:
            return "暂无日志记录"
        return "\n".join(
            f"[{r['created_at']}] [{r['level']}] {r['message']}"
            for r in reversed(rows))
    except Exception as e:
        return f"获取日志失败: {e}"
