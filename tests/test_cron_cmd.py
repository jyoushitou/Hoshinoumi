# ===================== !cron 命令测试（v17.7） =====================

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


class TestCronCommand(unittest.TestCase):
    """命令层：建任务、列任务、删/启停、参数校验"""

    def setUp(self):
        import botv.commands  # noqa: F401  确保注册
        from botv.cmd import registry
        from botv.schedule import cron

        self.cmd = registry.COMMANDS["cron"]
        self.cron = cron
        self.db = {}
        self._next_id = [1]
        self.hooked = []
        self._orig = (cron.add, cron.get, cron.list_tasks, cron.remove,
                      cron.set_enabled, cron.schedule_one, cron.cancel)

        def fake_add(uid, st, content, **kw):
            tid = self._next_id[0]
            self._next_id[0] += 1
            self.db[tid] = {
                "id": tid, "target_id": uid, "schedule_type": st,
                "content": content, "enabled": 1, "source": "command",
                "at_time": kw.get("at_time"), "weekdays": kw.get("weekdays"),
                "once_at": kw.get("once_at"), "interval_min": kw.get("interval_min"),
                "next_ts": "2026-11-12 07:30:00",
            }
            return tid

        cron.add = fake_add
        cron.get = lambda tid: self.db.get(int(tid))
        cron.list_tasks = lambda uid=None, **kw: list(self.db.values())
        cron.remove = lambda tid: self.db.pop(int(tid), None) is not None
        cron.set_enabled = lambda tid, on: bool(
            self.db.get(int(tid)) and self.db[int(tid)].update(enabled=1 if on else 0) is None)
        cron.schedule_one = lambda task, loop=None, scheduler=None: self.hooked.append(task["id"]) or True
        cron.cancel = lambda tid: True

    def tearDown(self):
        (self.cron.add, self.cron.get, self.cron.list_tasks, self.cron.remove,
         self.cron.set_enabled, self.cron.schedule_one, self.cron.cancel) = self._orig

    def _run(self, text):
        from botv.cmd.registry import CommandContext

        ctx = CommandContext(parts=text.split(), uid="822891053",
                             ws=None, is_group=False, gid=0)
        return asyncio.run(self.cmd.handler(ctx))

    def test_empty_list_shows_help(self):
        out = self._run("!cron")
        self.assertIn("还没有定时消息", out)

    def test_add_daily(self):
        out = self._run("!cron add 07:30 daily 叫我起床")
        self.assertIn("建好了", out)
        self.assertIn("每天 07:30", out)
        self.assertEqual(self.hooked, [1], "建完立刻挂钩子")

    def test_add_weekly_chinese(self):
        out = self._run("!cron add 20:00 一,三,五 健身")
        self.assertIn("建好了", out)
        task = self.db[1]
        self.assertEqual(task["schedule_type"], "weekly")
        self.assertEqual(task["weekdays"], "1,3,5", "中文星期应转数字")

    def test_add_weekly_english(self):
        self._run("!cron add 20:00 mon,fri 健身")
        self.assertEqual(self.db[1]["weekdays"], "mon,fri")

    def test_bad_time_rejected(self):
        out = self._run("!cron add 25:99 daily 测试")
        self.assertIn("时间格式", out)
        self.assertEqual(self.db, {})

    def test_once(self):
        out = self._run("!cron once 2026-11-15 09:00 交报告")
        self.assertIn("建好了", out)
        self.assertEqual(self.db[1]["schedule_type"], "once")
        self.assertIn("2026-11-15 09:00", self.db[1]["once_at"])

    def test_once_bad_date(self):
        out = self._run("!cron once 2026-13-45 09:00 x")
        self.assertIn("日期格式", out)

    def test_every(self):
        out = self._run("!cron every 30 喝口水")
        self.assertIn("建好了", out)
        self.assertEqual(self.db[1]["interval_min"], 30)

    def test_every_too_frequent(self):
        out = self._run("!cron every 1 烦死")
        self.assertIn("最少 5 分钟", out)

    def test_del(self):
        self._run("!cron add 07:30 daily x")
        out = self._run("!cron del 1")
        self.assertIn("已删除", out)
        self.assertEqual(self.db, {})

    def test_off_then_on(self):
        self._run("!cron add 07:30 daily x")
        out = self._run("!cron off 1")
        self.assertIn("已停用", out)
        self.assertEqual(self.db[1]["enabled"], 0)
        out = self._run("!cron on 1")
        self.assertIn("已启用", out)
        self.assertEqual(self.db[1]["enabled"], 1)

    def test_list_format(self):
        self._run("!cron add 07:30 daily 叫我起床")
        out = self._run("!cron list")
        self.assertIn("#1", out)
        self.assertIn("叫我起床", out)
        self.assertIn("命令", out, "来源应标出来")

    def test_unknown_subcommand(self):
        out = self._run("!cron foo")
        self.assertIn("不认识", out)

    def test_help(self):
        out = self._run("!cron help")
        self.assertIn("!cron add", out)


if __name__ == "__main__":
    unittest.main()
