# ===================== Worker 池（v17.1.0） =====================
# 从队列取事件、执行、按策略处理超时/重试/熔断。
#
# 三档槽位：
#   P0 聊天：快车道（与 P1 共用，但优先取）
#   P1 事件：快车道
#   P2 空闲：慢车道（有空时也帮 P1）
#
# 为什么要分车道：P2 任务再多也不能占满所有槽位，否则 P0 聊天要排队。

import asyncio
import time

from ..events.base import Priority
from ..log import log_api, log_err
from .policy import Breaker, classify, retry_delay, should_retry

FAST = (Priority.CHAT, Priority.EVENT)
SLOW = (Priority.EVENT, Priority.IDLE)


class WorkerPool:
    """按优先级分槽的事件执行器"""

    def __init__(self, queue, idle_workers=2, event_workers=1,
                 breaker=None, clock=None):
        self.queue = queue
        self.idle_slots = max(1, idle_workers)
        self.event_slots = max(1, event_workers)
        self.breaker = breaker or Breaker()
        self._clock = clock or time.time
        self._running = 0
        self._done = 0
        self._failed = 0
        self._timeouts = 0
        self._retries = 0
        self._by_kind = {}
        self._stopped = True
        self._tasks = []

    # ---------- 启动/停止 ----------

    def start(self):
        """起 worker 协程（在事件循环里调）"""
        if self._tasks:
            return
        self._stopped = False
        loop = asyncio.get_running_loop()   # 必须在事件循环里启动
        for _ in range(self.event_slots):
            self._tasks.append(loop.create_task(self._worker(FAST)))
        for _ in range(self.idle_slots):
            self._tasks.append(loop.create_task(self._worker(SLOW)))

    async def stop(self, timeout=10):
        """停止接新任务，给在跑的一点时间收尾"""
        self._stopped = True
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    # ---------- 主循环 ----------

    async def _worker(self, priorities):
        while not self._stopped:
            ev = self.queue.get_from(priorities)
            if ev is None:
                await asyncio.sleep(0.05)
                continue
            await self._execute(ev)

    # ---------- 执行 ----------

    async def _execute(self, ev):
        """跑一个事件：熔断检查 → 超时 → 重试 → 计数"""
        kind = ev.kind

        if self.breaker.is_open(kind, now=self._clock()):
            log_api(f"[调度] 跳过 {ev}：{kind} 熔断中"
                    f"（剩 {self.breaker.remaining(kind):.0f}s）")
            self.queue.drop(ev)
            return False

        attempt = 0
        limit = max(1, int(getattr(ev, "retries", 1) or 1))

        try:
            while True:
                attempt += 1
                self._running += 1
                try:
                    await asyncio.wait_for(
                        ev.fn(), timeout=getattr(ev, "timeout", 120) or None)
                    self._done += 1
                    self._count(kind, ok=True)
                    self.breaker.record_success(kind)
                    return True
                except asyncio.CancelledError:
                    self._count(kind, ok=False)
                    raise
                except Exception as e:
                    cat = classify(e)
                    if cat == "timeout":
                        self._timeouts += 1
                    log_err(f"[调度] {ev} 第 {attempt} 次失败（{cat}）：{e}")

                    if not should_retry(ev, e, attempt):
                        self._failed += 1
                        self._count(kind, ok=False)
                        if self.breaker.record_failure(kind, now=self._clock()):
                            log_err(f"[调度] {kind} 连续失败，"
                                    f"熔断 {self.breaker.cooldown:.0f}s")
                        return False

                    self._retries += 1
                    await asyncio.sleep(retry_delay(attempt))
                finally:
                    self._running = max(0, self._running - 1)
        finally:
            # 不管成败，最后都要解除去重，否则同 key 永远进不来
            self.queue.done(ev)

    # ---------- 统计 ----------

    def _count(self, kind, ok=True):
        item = self._by_kind.setdefault(kind, {"ok": 0, "fail": 0})
        item["ok" if ok else "fail"] += 1

    def stats(self):
        return {
            "running": self._running,
            "done": self._done,
            "failed": self._failed,
            "timeouts": self._timeouts,
            "retries": self._retries,
            "by_kind": dict(self._by_kind),
            "breaker": self.breaker.stats(),
            "queue": self.queue.stats(),
            "slots": {"idle": self.idle_slots, "event": self.event_slots},
        }
