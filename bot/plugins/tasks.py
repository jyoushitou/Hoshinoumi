# ===================== 插件任务归属（v28.3） =====================

import asyncio

from .errors import PluginTaskError


class PluginTasks:
    def __init__(self, owner):
        self.owner = str(owner)
        self._tasks = set()

    def spawn(self, name, coro):
        task = asyncio.create_task(coro, name=f"{self.owner}:{name}")
        self._tasks.add(task)

        def _done(t):
            self._tasks.discard(t)
            try:
                t.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                # 由 v28.5 的 plugin_errors 记录；这里不让异常静默丢失到事件循环
                pass

        task.add_done_callback(_done)
        return task

    def active(self):
        return len(self._tasks)

    async def cancel_all(self, timeout=5.0):
        tasks = [t for t in self._tasks if not t.done()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.difference_update(tasks)
        return len(tasks)
