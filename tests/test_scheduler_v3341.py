# ===================== v33.4.1.1 Scheduler 契约 + asyncio native =====================
import asyncio
import unittest
from datetime import datetime, timedelta

from bot.ports.scheduler import Scheduler
from bot.scheduling.native import AsyncioScheduler


class T:
    name = "t"
    async def next_at(self, now):
        return datetime.now() + timedelta(hours=1)


class TestSchedulerV3341(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(AsyncioScheduler(), Scheduler)

    def test_schedule_cancel(self):
        async def run():
            s = AsyncioScheduler(); await s.start()
            tid = await s.schedule(T(), lambda: None)
            self.assertTrue(tid)
            await s.cancel(tid)
            await s.stop()
        asyncio.run(run())

    def test_not_started(self):
        async def run():
            with self.assertRaises(RuntimeError):
                await AsyncioScheduler().schedule(T(), lambda: None)
        asyncio.run(run())


if __name__ == "__main__": unittest.main()
