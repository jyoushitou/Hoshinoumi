# ===================== 池监护线程（v17.8） =====================
# 线程池和连接池共用一个后台线程。
#
#     start_monitor()   启动（幂等）
#     stop_monitor()    停止
#     describe()        给 !stats 一行
#
# 职责：每 60 秒看一眼两个池的指标，发现异常就记日志。
# 不做业务、不碰数据库——它是观测者，不能自己成为被观测对象。

import threading
import time

from ..log import log_api, log_err

DEFAULT_INTERVAL = float(__import__("os").getenv("NAO_MONITOR_INTERVAL", "60"))
_ALERT_QUEUE = 3          # 线程池排队达到这个数就警告


class PoolMonitor:
    def __init__(self, interval=DEFAULT_INTERVAL, on_alert=None):
        self.interval = interval
        self._on_alert = on_alert
        self._thread = None
        self._stop = threading.Event()
        self._beats = 0
        self._last = {}
        self._last_alert = []

    # ---------- 生命周期 ----------

    def start(self):
        if self._thread and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="nao-pool-monitor", daemon=True)
        self._thread.start()
        log_api(f"[监护] 已启动（每 {self.interval:.0f}s 看线程池 + 连接池）")
        return self._thread

    def stop(self, timeout=2.0):
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        self._thread = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    # ---------- 主循环 ----------

    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                self.check_once()
            except Exception as e:      # 监护线程自身不能挂
                log_err(f"[监护] 检查失败: {e}")

    def check_once(self):
        self._beats += 1
        snap = self.snapshot()
        self._alert(snap)
        self._last = snap
        return snap

    # ---------- 快照 ----------

    def snapshot(self):
        from . import pool as db_pool
        from .blocking import thread_stats

        out = {"ts": time.time(), "threads": None, "db": None}
        try:
            out["threads"] = thread_stats()
        except Exception as e:
            out["threads"] = {"error": str(e)}
        try:
            out["db"] = db_pool.conn_stats()
        except Exception as e:
            out["db"] = {"error": str(e)}
        return out

    def _alert(self, snap):
        msgs = []
        th = snap.get("threads") or {}
        db = snap.get("db") or {}

        queued = th.get("queued")
        if isinstance(queued, int) and queued >= _ALERT_QUEUE:
            msgs.append(f"线程池排队 {queued}（槽位 {th.get('size')}）")

        if isinstance(db, dict) and "error" not in db:
            idle, size, borrowed = db.get("idle"), db.get("size"), db.get("borrowed")
            if isinstance(idle, int) and size and idle == 0 and borrowed == size:
                msgs.append(f"连接池全借出（{borrowed}/{size}），可能泄漏")
            if (db.get("timeouts") or 0) > 0:
                msgs.append(f"借连接超时 {db.get('timeouts')} 次")

        self._last_alert = msgs
        if msgs:
            log_err("[监护] " + "；".join(msgs))
            if self._on_alert:
                try:
                    self._on_alert(msgs)
                except Exception:
                    pass
        return msgs

    # ---------- 观测 ----------

    def stats(self):
        return {"running": self.running, "beats": self._beats,
                "interval": self.interval, "last": self._last,
                "alerts": self._last_alert}


_monitor = None


def get_monitor():
    global _monitor
    if _monitor is None:
        _monitor = PoolMonitor()
    return _monitor


def start_monitor(interval=None):
    m = get_monitor()
    if interval:
        m.interval = interval
    return m.start()


def stop_monitor():
    if _monitor is not None:
        _monitor.stop()


def describe():
    m = get_monitor()
    if not m.running:
        return "🩺 监护：未启动"
    s = m.stats()
    last = s.get("last") or {}
    th = last.get("threads") or {}
    db = last.get("db") or {}
    parts = [f"🩺 监护：{s['beats']} 次"]
    if th and "size" in th:
        parts.append(f"线程 {th.get('size')} 排队 {th.get('queued')}")
    if db and "error" not in db:
        parts.append(f"连接 {db.get('idle')}/{db.get('size')}")
    return " | ".join(parts)
