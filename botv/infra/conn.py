# ===================== 数据库连接 =====================
# 线程本地连接（每个线程独立），迁移自 db.py（v5-R6）

import threading

import pymysql

from ..config import DB_CONFIG

_local = threading.local()  # 线程本地存储（每个线程独立数据库连接）


def get_db():
    """获取当前线程的数据库连接（懒加载）"""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)  # 创建连接，返回字典游标
    return _local.conn


def get_cursor():
    """获取数据库游标"""
    return get_db().cursor()
