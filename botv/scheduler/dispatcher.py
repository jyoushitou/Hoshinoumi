# ===================== 调度器入口（v17.1.0） =====================
# 把「队列 + worker 池 + 注册表」串成一个对象，对外只暴露三个动作：
#
#     sched = Scheduler()
#     sched.start()                      # 起 worker
#     sched.submit(kind, key, **kwargs)  # 投递事件（自动查注册表拿 handler）
#     await sched.stop()                 # 收尾
#
# 设计要点：
#   - submit 时自动校验 kind 已注册（拼错立刻报错）
#   - priority/timeout 缺省时从注册表继承
#   - 用法上没有 await：投递是同步的（只是塞队列），这样聊天路径调它不丢控制权
#   - stats() 汇总队列 + worker + 熔断，给 !stats 用

import asyncio
import functools

from ..events import registry
from ..events.base import Priority
from ..log import log_api
from .queue import EventQueue
from .workers import WorkerPool


class Scheduler:
    """统一的事件调度器"""

    def __init__(self, idle_workers=2, event_workers=1, idle_limit=50):
        self.queue = EventQueue(idle_limit=idle_limit)
        self.pool = WorkerPool(self.queue, idle_workers=idle_workers,
                               event_workers=event_workers)
        self._started = False

    # ---------- 生命周期 ----------

    def start(self):
        """起 worker（幂等）"""
        if not self._started:
            self.pool.start()
            self._started = True
            log_api(f"[调度] 已启动：{self.pool.event_slots} 快 / "
                    f"{self.pool.idle_slots} 慢")

    async def stop(self, timeout=10):
        if self._started:
            await self.pool.stop(timeout=timeout)
            self._started = False
            log_api("[调度] 已停止")

    # ---------- 投递 ----------

    def submit(self, kind, key, args=(), priority=None, timeout=None, retries=None):
        """投递一个事件；返回是否入队成功

        - kind 必须已注册，否则抛 KeyError（早发现拼错）
        - priority/timeout 不传就用注册表里的默认值
        """
        from ..events.base import Event

        handler = registry.require(kind)          # 未注册直接抛错

        prio = handler.priority if priority is None else priority
        tmo = handler.timeout if timeout is None else timeout
        ret = handler.retries if retries is None else retries

        fn = functools.partial(handler.fn, args) if args else functools.partial(handler.fn, None)
        ev = Event(kind=kind, key=key, fn=fn, priority=prio,
                   timeout=tmo, retries=ret)
        ok = self.queue.put(ev)
        if not ok:
            log_api(f"[调度] 丢弃重复事件 {ev}")
        return ok

    # ---------- 观测 ----------

    def stats(self):
        s = self.pool.stats()
        by_kind = registry.snapshot()
        s["kinds"] = by_kind
        s["started"] = self._started
        return s

    def describe(self):
        """给 !stats 的几行文本"""
        s = self.stats()
        q = s.get("queue", {})
        lines = [
            f"⚙️ 调度：{'运行中' if s['started'] else '已停止'} | "
            f"队列 {q.get('total', 0)}（聊天 {q.get('chat', 0)} / "
            f"定时 {q.get('event', 0)} / 空闲 {q.get('idle', 0)}）",
            f"   完成 {s.get('done', 0)} | 失败 {s.get('failed', 0)} | "
            f"超时 {s.get('timeouts', 0)} | 重试 {s.get('retries', 0)}",
        ]
        open_kinds = s.get("breaker", {}).get("open_kinds") or []
        if open_kinds:
            lines.append(f"   ⚠️ 熔断中：{', '.join(open_kinds)}")
        return "\n".join(lines)


_global = None


def get_scheduler():
    """全局调度器（懒加载，延迟到事件循环里 start）"""
    global _global
    if _global is None:
        _global = Scheduler()
    return _global


def set_scheduler(sched):
    """测试用"""
    global _global
    _global = sched
