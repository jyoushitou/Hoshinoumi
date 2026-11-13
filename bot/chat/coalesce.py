# ===================== 连发合并（v17.3 U2） =====================
# 问题：主人连着发三句「在吗」「问你个事」「那个…」，她每句都回一次，很吵。
#
# 目标：
#   - 连发只回**一次**，且信息完整（三句一起看）
#   - **单条延迟不变**（不能因为合并让一句话等 2 秒）
#
# 做法（防抖 + 总窗口）：
#   第一条进来 → 开防抖计时器 DEBOUNCE（0.6 秒）
#   防抖期内又来 → 追加，静默时间重新计
#   静默够 DEBOUNCE 或总时长到 WINDOW → 整批交给 handler 处理一次
#
#   单条：多等 0.6 秒（相对 1.5~3 秒回复延迟可忽略）
#   连发：合并成一批，只回一次

import asyncio

from ..log import log_api, log_err

DEBOUNCE = 0.6      # 静默多久算「说完了」
WINDOW = 2.0        # 从第一条开始最多等多久
MAX_ITEMS = 5       # 一批最多几条


class Coalescer:
    """按目标聚合连发的消息"""

    def __init__(self, handler, debounce=DEBOUNCE, window=WINDOW, max_items=MAX_ITEMS):
        self._handler = handler          # async (target, [items]) -> None
        self.debounce = debounce
        self.window = window
        self.max_items = max_items
        self._batches = {}               # target -> {"items", "started", "last", "task"}
        self._merged = 0                 # 省下的回复次数
        self._flushes = 0

    async def offer(self, target, item):
        """投一条消息；返回 True 表示已缓存（稍后统一处理）"""
        loop = asyncio.get_running_loop()
        now = loop.time()

        batch = self._batches.get(target)
        if batch is None:
            batch = {"items": [item], "started": now, "last": now, "task": None}
            self._batches[target] = batch
            batch["task"] = loop.create_task(self._wait_and_flush(target))
            return True

        batch["items"].append(item)
        batch["last"] = now
        if len(batch["items"]) >= self.max_items:
            await self._flush(target)
            return True
        return True

    async def flush_all(self):
        """退出时把剩下的都处理掉"""
        for target in list(self._batches):
            await self._flush(target)

    # ---------- 内部 ----------

    async def _wait_and_flush(self, target):
        """静默够 debounce，或总时长到 window，就 flush"""
        loop = asyncio.get_running_loop()
        try:
            while True:
                await asyncio.sleep(self.debounce)
                batch = self._batches.get(target)
                if batch is None:
                    return
                now = loop.time()
                silent = now - batch["last"] >= self.debounce
                expired = now - batch["started"] >= self.window
                if silent or expired:
                    await self._flush(target)
                    return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_err(f"[合并] 等待失败: {e}")

    async def _flush(self, target):
        batch = self._batches.pop(target, None)
        if not batch:
            return False

        task = batch.get("task")
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()

        items = batch["items"]
        self._flushes += 1
        if len(items) > 1:
            self._merged += len(items) - 1
            log_api(f"[合并] {target} 连发 {len(items)} 条，合并处理")

        try:
            await self._handler(target, items)
        except Exception as e:
            log_err(f"[合并] 处理失败: {e}")
            return False
        return True

    # ---------- 观测 ----------

    def pending(self, target=None):
        if target is None:
            return sum(len(b["items"]) for b in self._batches.values())
        b = self._batches.get(target)
        return len(b["items"]) if b else 0

    def stats(self):
        return {
            "pending": self.pending(),
            "batches": len(self._batches),
            "merged": self._merged,
            "flushes": self._flushes,
            "debounce": self.debounce,
            "window": self.window,
        }
