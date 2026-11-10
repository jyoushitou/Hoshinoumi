# ===================== 优先级事件队列（v17.1.0） =====================
# 三档优先级 + 去重 + 批量取。
#
#     q = EventQueue()
#     q.put(ev)                 # 入队（同 dedupe_key 未完成时丢弃）
#     ev = q.get_nowait()       # 取优先级最高的一条
#     q.done(ev)                # 标记完成（解除去重）
#
# 设计要点：
#   - 用「三个 deque」而不是堆：优先级只有三档，deque 的 FIFO 语义更直观
#   - 去重表在「入队时登记、done 时解除」——任务在跑期间不会重复入队
#   - 容量上限只限制 P2（空闲），P0/P1 永不因容量被丢
#   - 所有操作都是同步的（不 await），调度器在事件循环里调它不会让出控制权

import time
from collections import deque

from ..events.base import Priority


class EventQueue:
    """三档优先级队列"""

    def __init__(self, idle_limit=50):
        self.idle_limit = idle_limit
        self._lanes = {
            Priority.CHAT: deque(),
            Priority.EVENT: deque(),
            Priority.IDLE: deque(),
        }
        self._inflight = {}          # dedupe_key -> Event（在跑或待跑）
        self._dropped = 0            # 因去重/容量丢弃的数量
        self._put_total = 0

    # ---------- 入队 ----------

    def put(self, ev, now=None):
        """入队；同 dedupe_key 已存在时返回 False（丢弃）"""
        key = ev.dedupe_key()
        if key in self._inflight:
            self._dropped += 1
            return False

        lane = self._lanes.get(int(ev.priority))
        if lane is None:                       # 未知优先级当空闲处理
            lane = self._lanes[Priority.IDLE]

        if lane is self._lanes[Priority.IDLE] and len(lane) >= self.idle_limit:
            # 空闲队列满了：丢最旧的（不丢新的，新的可能更重要）
            old = lane.popleft()
            self._inflight.pop(old.dedupe_key(), None)
            self._dropped += 1

        lane.append(ev)
        self._inflight[key] = ev
        self._put_total += 1
        return True

    # ---------- 出队 ----------

    def get_nowait(self):
        """按 CHAT → EVENT → IDLE 取一条；空返回 None"""
        for prio in (Priority.CHAT, Priority.EVENT, Priority.IDLE):
            lane = self._lanes[prio]
            if lane:
                return lane.popleft()
        return None

    def peek(self):
        """看一眼下一条会取谁（不弹出）"""
        for prio in (Priority.CHAT, Priority.EVENT, Priority.IDLE):
            lane = self._lanes[prio]
            if lane:
                return lane[0]
        return None

    def done(self, ev):
        """标记完成，解除去重；同一 key 可以再次入队"""
        self._inflight.pop(ev.dedupe_key(), None)

    def drop(self, ev):
        """放弃某个事件（超时/取消），等同 done"""
        self._inflight.pop(ev.dedupe_key(), None)

    # ---------- 观测 ----------

    def __len__(self):
        return sum(len(lane) for lane in self._lanes.values())

    def qsize(self, priority=None):
        if priority is None:
            return len(self)
        return len(self._lanes.get(int(priority), ()))

    def stats(self):
        return {
            "total": len(self),
            "chat": len(self._lanes[Priority.CHAT]),
            "event": len(self._lanes[Priority.EVENT]),
            "idle": len(self._lanes[Priority.IDLE]),
            "inflight": len(self._inflight),
            "dropped": self._dropped,
            "put_total": self._put_total,
        }

    def clear(self):
        for lane in self._lanes.values():
            lane.clear()
        self._inflight.clear()
