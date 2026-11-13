# ===================== 数据库连接（v17.11：MySQL / SQLite 可选） =====================
# 线程本地连接（每个线程独立）。
#
# 后端由 config.local.json 的 db.backend 决定：
#   mysql  → pymysql（默认，行为不变）
#   sqlite → 标准库 sqlite3，一个文件搞定
#
# 两种后端都返回「字典行」+ 支持 %s 占位符的游标，
# 上层代码不用区分后端。

import sqlite3
import threading

_local = threading.local()  # 线程本地存储（每个线程独立数据库连接）

# ===================== 配置注入（v17.14 债一） =====================
# 以前这里 import settings，settings 又 import log，log 又 import db…
# 现在改成：**谁用谁注入**。app/bootstrap.py 启动时调一次 configure()。
# 没注入时退回旧的懒加载（兼容脚本/测试），但那是唯一残留的边。

_config = {"backend": None, "mysql": None, "sqlite_path": None}


def configure(mysql_config=None, backend=None, sqlite_path=None):
    """注入数据库配置；bootstrap 启动时调一次

    mysql_config 形如 {"host":..., "port":..., "user":..., "password":..., "database":...}
    """
    _config["mysql"] = dict(mysql_config) if mysql_config else None
    _config["backend"] = backend
    _config["sqlite_path"] = sqlite_path
    # 配置变了，旧连接作废
    try:
        _local.__dict__.clear()
    except Exception:
        pass
    return _config


def configured():
    """有没有注入过配置（测试用）"""
    return _config["backend"] is not None


def _resolve_backend():
    if _config["backend"]:
        return _config["backend"]
    from ..core.settings import storage_backend   # 兼容路径：仅未注入时走

    return storage_backend()


def _resolve_mysql():
    if _config["mysql"]:
        return _config["mysql"]
    from ..core.constants import DB_CONFIG        # 兼容路径：仅未注入时走

    return DB_CONFIG


def _resolve_sqlite_path():
    if _config["sqlite_path"]:
        return _config["sqlite_path"]
    from ..core.settings import sqlite_path

    return sqlite_path()


class _SQLiteCursor:
    """把 sqlite3 游标包装成 pymysql 的样子：%s 占位符 + 字典行"""

    def __init__(self, cur, conn):
        self._cur = cur
        self.connection = conn        # 让 c.connection.commit() 也能用

    def execute(self, sql, params=None):
        # pymysql 用 %s，sqlite 用 ?
        sql = sql.replace("%s", "?")
        if params is None:
            return self._cur.execute(sql)
        return self._cur.execute(sql, params)

    def executemany(self, sql, seq):
        sql = sql.replace("%s", "?")
        return self._cur.executemany(sql, seq)

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        return self._cur.close()


def _connect_sqlite():
    path = _resolve_sqlite_path()
    import os

    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")     # 读写不互相锁死
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    """获取当前线程的数据库连接（懒加载）"""
    if not hasattr(_local, "conn") or _local.conn is None:
        backend = _resolve_backend()
        if not getattr(_local, "announced", False):
            _local.announced = True
            try:
                # 只打印，不走日志系统——log_system 会连库，连库又会到这里
                print(f"[存储] 使用后端：{backend}"
                      + ("（文件数据库）" if backend == "sqlite" else ""))
            except Exception:
                pass
        if backend == "sqlite":
            _local.conn = _connect_sqlite()
        else:
            import pymysql

            _local.conn = pymysql.connect(
                **_resolve_mysql(), cursorclass=pymysql.cursors.DictCursor)
    return _local.conn


def get_cursor():
    """获取数据库游标（两种后端统一接口）"""
    conn = get_db()
    if _resolve_backend() == "sqlite":
        return _SQLiteCursor(conn.cursor(), conn)
    return conn.cursor()
