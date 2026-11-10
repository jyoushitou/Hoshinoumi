# ===================== 连发合并窗口（v17.2 U3） =====================
# 解决的问题：两条定时消息隔几秒到，各发一条气泡，看起来像刷屏。
#
# 规则：
#   - 只合并**相邻的定时消息**（kind 属于 MERGEABLE）
#   - 窗口 3 秒：第一条进来时开窗，窗口内后续消息合并
#   - 窗口到期、或凑够条数、或来了不可合并的消息 → 立即发
#   - 聊天回复、命令、图片、语音**永不合并**（各走各的）
#
# 为什么聊天不合并：聊天是「你问我答」，合并会破坏对话节奏；
# 定时消息是「她主动说」，合并成一条更自然。

import asyncio
import time

from ..log import log_api

WINDOW = 3.0             # 合并窗口（秒）
MAX_ITEMS = 3            # 一个窗口最多合几条
MERGEABLE = {"schedule"}  # 哪些 kind 允许合并


class Merger:
    """按目标聚合文本，窗口到期后一次性发出"""

    def __init__(self, send=None, window=WINDOW, max_items=MAX_ITEMS, clock=None):
        self._send = send              # async (target, texts) -> bool
        self.window = window
        self.max_items = max_items
        self._clock = clock or time.time
        self._buckets = {}             # target -> {"texts": [...], "task": Task}
        self._merged = 0               # 合并掉几次（省下多少条）
        self._flushed = 0              # 实际发出几条

    # ---------- 入口 ----------

    async def offer(self, target, text, kind="schedule"):
        """尝试把一条文本放进窗口；返回 True 表示已缓存（稍后合并发）"""
        if kind not in MERGEABLE or not text:
            return False

        bucket = self._buckets.get(target)
        if bucket is None:
            loop = asyncio.get_running_loop()
            bucket = {"texts": [text], "task": loop.create_task(self._flush_later(target))}
            self._buckets[target] = bucket
            return True

        bucket["texts"].append(text)
        if len(bucket["texts"]) >= self.max_items:
            await self._flush(target)
            return True
        return True

    async def flush_all(self):
        """立刻发完所有窗口（退出时用）"""
        for target in list(self._buckets):
            await self._flush(target)

    # ---------- 内部 ----------

    async def _flush_later(self, target):
        await asyncio.sleep(self.window)
        await self._flush(target)

    async def _flush(self, target):
        bucket = self._buckets.pop(target, None)
        if not bucket:
            return False

        texts = bucket["texts"]
        task = bucket["task"]
        if task is not asyncio.current_task() and not task.done():
            task.cancel()

        if len(texts) > 1:
            self._merged += len(texts) - 1
            text = self._join(texts)
            log_api(f"[合并] {target} 的 {len(texts)} 条并成 1 条")
        else:
            text = texts[0]

        self._flushed += 1
        if self._send is not None:
            try:
                await self._send(target, text)
            except Exception as e:
                from ..log import log_err
                log_err(f"[合并] 发送失败: {e}")
                return False
        return True

    def _join(self, texts):
        """拼接：用换行，去掉重复的完全相同的句子"""
        out = []
        for t in texts:
            t = (t or "").strip()
            if t and (not out or out[-1] != t):
                out.append(t)
        return "\n".join(out)

    # ---------- 观测 ----------

    def pending(self, target=None):
        if target is None:
            return sum(len(b["texts"]) for b in self._buckets.values())
        bucket = self._buckets.get(target)
        return len(bucket["texts"]) if bucket else 0

    def stats(self):
        return {
            "pending": self.pending(),
            "merged": self._merged,
            "flushed": self._flushed,
            "window": self.window,
            "targets": len(self._buckets),
        }
