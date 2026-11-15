# ===================== v27.0 一次性任务清理 =====================
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m


class _Cursor:
    def __init__(self):
        self.sql = []
        self.connection = self

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def commit(self):
        pass


class TestOnceCleanup(unittest.TestCase):
    def test_successful_once_is_removed(self):
        import bot.executors.cron as ex

        cur = _Cursor()
        with mock.patch("bot.infra.conn.get_cursor", return_value=cur), \
             mock.patch("bot.schedule.cron.get", return_value={
                 "id": 11, "user_id": "822891053", "schedule_type": "once"}), \
             mock.patch("bot.schedule.cron.remove", return_value=True) as rm, \
             mock.patch("bot.schedule.cron.cancel") as cancel:
            ex._mark(11, ok=True)
        rm.assert_called_once_with(11, user_id="822891053")
        cancel.assert_called_once_with(11)
        self.assertFalse(any("UPDATE cron_tasks" in s for s, _ in cur.sql))

    def test_failed_once_is_not_removed(self):
        import bot.executors.cron as ex

        cur = _Cursor()
        with mock.patch("bot.infra.conn.get_cursor", return_value=cur), \
             mock.patch("bot.schedule.cron.get", return_value={
                 "id": 12, "user_id": "822891053", "schedule_type": "once"}), \
             mock.patch("bot.schedule.cron.remove") as rm, \
             mock.patch("bot.schedule.cron.cancel") as cancel:
            ex._mark(12, ok=False)
        rm.assert_not_called()
        cancel.assert_not_called()
        self.assertTrue(any("UPDATE cron_tasks" in s for s, _ in cur.sql))


if __name__ == "__main__":
    unittest.main()
