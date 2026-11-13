# ===================== 定时场景执行器测试（v17.1.0） =====================

import asyncio
import sys
import types
import unittest


def _stub_missing_deps():
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None

    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)


_stub_missing_deps()


class _Ev:
    def __init__(self, args=()):
        self.args = args
        self.kind = "schedule_scene"


class TestScheduleExecutor(unittest.TestCase):
    """场景表完整、执行会发消息、未知场景有兜底、一天一次靠 key 去重"""

    def setUp(self):
        import bot.executors.schedule as S
        from bot.scheduler.dispatcher import Scheduler, set_scheduler

        self.S = S
        self.sched = Scheduler()
        set_scheduler(self.sched)
        self.sent = []

        from bot.ai import client as C
        from bot.chat import send as SEND

        self._orig = (C.get_character_reply, SEND.send_short_reply)
        C.get_character_reply = lambda prompt, tid: _async("定时的一句")
        SEND.send_short_reply = lambda *a, **k: _async(self.sent.append(a))

    def tearDown(self):
        from bot.ai import client as C
        from bot.chat import send as SEND
        from bot.scheduler.dispatcher import set_scheduler

        C.get_character_reply, SEND.send_short_reply = self._orig
        set_scheduler(None)

    def test_all_builtin_scenes_present(self):
        for name in ("催起床", "催睡觉", "提醒点外卖", "叮嘱午睡",
                     "提醒起身", "提醒晚餐", "周日复盘", "周末吐槽赖床"):
            self.assertIn(name, self.S.SCENES, f"缺少场景 {name}")

    def test_scene_has_prompts(self):
        for name, conf in self.S.SCENES.items():
            self.assertTrue(conf.get("prompts"), f"{name} 没有提示词")

    def test_unknown_scene_fallback(self):
        conf = self.S.scene_config("不存在的场景")
        self.assertEqual(conf["prompts"], self.S.DEFAULT_PROMPTS)

    def test_execute_sends(self):
        """v17.2：执行后进合并窗口，flush 才真正发出"""
        from bot.egress.merge import Merger, set_merger

        got = []

        async def send(target, text):
            got.append((target, text))

        merger = Merger(send=send, window=0.05)
        set_merger(merger)

        async def main():
            out = await self.S.handle_schedule_scene(_Ev(args=("提醒晚餐",)))
            await merger.flush_all()
            return out

        out = asyncio.run(main())
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(got), 1, "合并窗口应发出 1 条")
        self.assertIn("定时的一句", got[0][1])

    def test_submit_scene_dedupes_by_day(self):
        self.assertTrue(self.S.submit_scene("催起床", "2026-11-10"))
        self.assertFalse(self.S.submit_scene("催起床", "2026-11-10"), "同一天不该重复")
        self.assertTrue(self.S.submit_scene("催起床", "2026-11-11"), "换一天可以")

    def test_with_image_flag(self):
        self.assertTrue(self.S.SCENES["催起床"].get("with_image"))
        self.assertFalse(self.S.SCENES["提醒晚餐"].get("with_image"))


async def _async(value):
    return value


if __name__ == "__main__":
    unittest.main()
