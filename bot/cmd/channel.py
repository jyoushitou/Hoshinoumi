# ===================== 命令通道（v17.2 U4） =====================
# 命令必须秒回——哪怕调度器队列堆满、worker 全在跑读书任务。
#
# 做法：
#   - 命令**不进调度器队列**，在收到的那一刻直接执行（P0 里的 P0）
#   - 用独立信号量限制并发（默认 2）：命令之间不互相踩
#   - 每条命令有超时（默认 15 秒），卡住就回「超时」而不是静默
#   - 记录耗时：哪个命令慢，一眼看得出来
#
# 为什么不用调度器：调度器是为「可以等」的任务设计的（读书、定时）。
# 命令是「人在等」，必须绕开队列。

import asyncio
import time

from ..log import log_api, log_err

COMMAND_TIMEOUT = 15.0
MAX_CONCURRENT = 2


class CommandChannel:
    """命令专用执行通道"""

    def __init__(self, timeout=COMMAND_TIMEOUT, max_concurrent=MAX_CONCURRENT):
        self.timeout = timeout
        self._sem = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self._count = 0
        self._timeouts = 0
        self._errors = 0
        self._total_ms = 0.0
        self._slowest = ("", 0.0)
        self._by_cmd = {}

    async def run(self, name, fn, *args, **kwargs):
        """执行一个命令协程；返回 (ok, result_or_error)

        fn 是 `async def fn(*args)`，通常就是 registry.run(name, ctx)。
        """
        import time as _t

        started = _t.perf_counter()
        self._count += 1
        try:
            async with self._sem:
                result = await asyncio.wait_for(fn(*args, **kwargs), timeout=self.timeout)
            elapsed = (_t.perf_counter() - started) * 1000
            self._record(name, elapsed)
            return True, result
        except asyncio.TimeoutError:
            self._timeouts += 1
            elapsed = (_t.perf_counter() - started) * 1000
            self._record(name, elapsed)
            log_err(f"[命令] {name} 超时（{self.timeout:.0f}s）")
            return False, f"⏱️ 命令 {name} 超时（{self.timeout:.0f} 秒）"
        except Exception as e:
            self._errors += 1
            elapsed = (_t.perf_counter() - started) * 1000
            self._record(name, elapsed)
            log_err(f"[命令] {name} 出错: {e}")
            return False, f"❌ 命令 {name} 出错：{e}"

    def _record(self, name, ms):
        self._total_ms += ms
        item = self._by_cmd.setdefault(name, {"count": 0, "total_ms": 0.0, "max_ms": 0.0})
        item["count"] += 1
        item["total_ms"] += ms
        item["max_ms"] = max(item["max_ms"], ms)
        if ms > self._slowest[1]:
            self._slowest = (name, ms)

    # ---------- 观测 ----------

    def stats(self):
        avg = self._total_ms / self._count if self._count else 0.0
        return {
            "count": self._count,
            "timeouts": self._timeouts,
            "errors": self._errors,
            "avg_ms": round(avg, 1),
            "slowest": {"name": self._slowest[0], "ms": round(self._slowest[1], 1)},
            "by_cmd": {k: dict(v) for k, v in self._by_cmd.items()},
        }

    def describe(self):
        s = self.stats()
        if not s["count"]:
            return "⌨️ 命令：还没执行过"
        text = f"⌨️ 命令：{s['count']} 次 | 平均 {s['avg_ms']} ms"
        if s["slowest"]["ms"]:
            text += f" | 最慢 {s['slowest']['name']} {s['slowest']['ms']:.0f} ms"
        if s["timeouts"]:
            text += f" | 超时 {s['timeouts']}"
        if s["errors"]:
            text += f" | 出错 {s['errors']}"
        return text


_channel = None


def get_channel():
    global _channel
    if _channel is None:
        _channel = CommandChannel()
    return _channel


def set_channel(ch):
    global _channel
    _channel = ch
