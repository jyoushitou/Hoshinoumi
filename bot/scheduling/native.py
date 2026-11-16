# ===================== asyncio 调度 native（v33.4.1） =====================

import asyncio
import uuid

from ..ports.scheduler import Scheduler


class AsyncioScheduler:
    name = "asyncio"

    def __init__(self, loop=None):
        self.loop = loop
        self.started = False
        self._handles = {}

    async def start(self):
        self.started = True
        self.loop = self.loop or asyncio.get_event_loop()

    async def stop(self):
        for h in self._handles.values():
            h.cancel()
        self._handles.clear()
        self.started = False

    async def schedule(self, trigger, callback):
        if not self.started:
            raise RuntimeError("scheduler not started")
        now = asyncio.get_event_loop().time()
        next_at = await trigger.next_at(None)
        delay = max(0.0, next_at.timestamp() - __import__("time").time())
        task_id = uuid.uuid4().hex

        def fire():
            self._handles.pop(task_id, None)
            out = callback()
            if asyncio.iscoroutine(out):
                asyncio.create_task(out)

        self._handles[task_id] = self.loop.call_later(delay, fire)
        return task_id

    async def cancel(self, task_id):
        h = self._handles.pop(task_id, None)
        if h:
            h.cancel()


assert isinstance(AsyncioScheduler(), Scheduler)
