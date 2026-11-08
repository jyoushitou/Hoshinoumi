# ===================== 日志仓储 =====================
# 迁移自 db.py（v5-R6）

from datetime import datetime

from ..config import CST
from .conn import get_cursor


def write_log_to_db(level, msg):
    """写入日志到数据库logs表"""
    try:
        c = get_cursor()
        c.execute("INSERT INTO logs(level,message,created_at)VALUES(%s,%s,%s)",
                  (level, msg, datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')))
        c.connection.commit()
    except:
        pass  # 日志写入失败不影响主流程
