# ===================== 连接池（v17.0.2） =====================
# 现状：线程本地连接，每条线程一条，永不归还、断了不自愈。
# 问题：
#   - 线程数一多就顶到 MySQL 的 max_connections
#   - 连接断了（wait_timeout）只能等下次报错
#
# 连接池解决：
#   - 固定上限（默认 5），用完归还
#   - 借出前探活（ping），断了自动重建
#   - 借不到时**快速失败**（默认 5 秒），不无限等
#
# 约束：
#   - 池大小 ≥ 线程池大小（否则线程等连接，等于串行）
#   - 借了必还（try/finally 或 with）
#   - 不在长操作（调模型）期间持有连接

import os
import queue
import threading
import time

from ..log import log_api

DEFAULT_POOL_SIZE = int(os.getenv("NAO_DB_POOL_SIZE", "5"))
DEFAULT_ACQUIRE_TIMEOUT = float(os.getenv("NAO_DB_POOL_TIMEOUT", "5.0"))


def _default_connect():
    """真实连接（测试里会被替换）"""
    import pymysql

    from ..config import DB_CONFIG

    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


class ConnPool:
    """固定容量的 MySQL 连接池"""

    def __init__(self, size=None, timeout=None, connect=None):
        self.size = size if size is not None else DEFAULT_POOL_SIZE
        self.timeout = timeout if timeout is not None else DEFAULT_ACQUIRE_TIMEOUT
        self._connect = connect or _default_connect
        self._idle = queue.LifoQueue(maxsize=self.size)
        self._lock = threading.Lock()
        self._created = 0       # 累计创建过几条
        self._borrowed = 0      # 当前借出几条
        self._reused = 0        # 复用次数
        self._timeouts = 0      # 借不到的次数

    # ---------- 借还 ----------

    def acquire(self, timeout=None):
        """借一条连接；超时抛 TimeoutError"""
        wait = self.timeout if timeout is None else timeout

        try:
            conn = self._idle.get_nowait()
        except queue.Empty:
            # 还有额度就新建
            with self._lock:
                if self._created < self.size:
                    self._created += 1
                    conn = self._connect()
                    self._borrowed += 1
                    return conn
            # 没额度了，等别人还
            try:
                conn = self._idle.get(timeout=wait)
            except queue.Empty:
                self._timeouts += 1
                raise TimeoutError(f"连接池已满（{self.size} 条），等待 {wait:.1f}s 未果")

        if not self._healthy(conn):
            log_api("[conn-pool] 连接已断，重建")
            with self._lock:
                self._created += 1
            conn = self._connect()
        else:
            self._reused += 1

        with self._lock:
            self._borrowed += 1
        return conn

    def release(self, conn):
        """归还连接；已断的直接丢弃"""
        if conn is None:
            return
        with self._lock:
            self._borrowed = max(0, self._borrowed - 1)
        if self._healthy(conn):
            try:
                self._idle.put_nowait(conn)
                return
            except queue.Full:
                pass
        self._close(conn)

    # ---------- 健康检查 ----------

    def _healthy(self, conn):
        try:
            if not getattr(conn, "open", True):
                return False
            conn.ping(reconnect=False)
            return True
        except Exception:
            return False

    def _close(self, conn):
        try:
            conn.close()
        except Exception:
            pass

    # ---------- 统计 ----------

    def stats(self):
        return {
            "size": self.size,
            "idle": self._idle.qsize(),
            "borrowed": self._borrowed,
            "created": self._created,
            "reused": self._reused,
            "timeouts": self._timeouts,
        }

    def close_all(self):
        """进程退出时关掉所有空闲连接"""
        while True:
            try:
                self._close(self._idle.get_nowait())
            except queue.Empty:
                break


_pool = None
_pool_lock = threading.Lock()


def get_pool():
    """全局连接池（懒加载）"""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnPool()
    return _pool


def set_pool(pool):
    """测试用：替换全局池"""
    global _pool
    _pool = pool


class pooled_cursor:
    """with pooled_cursor() as c: ... 自动借还"""

    def __enter__(self):
        self.conn = get_pool().acquire()
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc, tb):
        try:
            self.cursor.close()
        except Exception:
            pass
        get_pool().release(self.conn)
        return False
