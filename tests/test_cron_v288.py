# ===================== v28.8 过期 once / 重复任务 =====================
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from datetime import datetime

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m


def task(tid, once_at, content="x", user_id="u", stype="once", **kw):
    d = {"id": tid, "user_id": user_id, "target_id": "t", "schedule_type": stype,
         "at_time": "", "weekdays": "", "once_at": once_at, "interval_min": None,
         "content": content, "enabled": 1, "rule": None, "timing": None,
         "next_ts": None}
    d.update(kw)
    return d


class TestCronReconcile(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        from bot.core import clock
        clock.use_fake(datetime(2026, 11, 16, 9, 0, 0))
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "c.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["cron_tasks"])
        try:
            self.c.execute("ALTER TABLE cron_tasks ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT '__owner__'")
        except Exception:
            pass
        self.c.connection.commit()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        from bot.core import clock
        clock.reset()
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_expired_once_deleted(self):
        from bot.schedule import cron
        self.c.execute(
            "INSERT INTO cron_tasks(id,user_id,target_id,schedule_type,once_at,content,enabled) "
            "VALUES(12,'u','t','once','2026-11-16 08:00:00','复习linux',1)")
        self.c.connection.commit()
        t = task(12, "2026-11-16 08:00:00", "复习linux")
        print("DEBUG nxt", cron.compute_next(t), "task", t)
        print("DEBUG remove", cron.remove, "self", getattr(cron.remove, "__self__", None))
        cron.schedule_all(tasks=[t])
        print("DEBUG direct", cron.remove(12, user_id="u"))
        self.c.execute("SELECT id,user_id FROM cron_tasks")
        print("DEBUG rows", self.c.fetchall())
        self.c.execute("SELECT COUNT(*) AS n FROM cron_tasks WHERE id=12")
        self.assertEqual(self.c.fetchone()["n"], 0)

    def test_duplicate_groups_only_report(self):
        from bot.schedule.cron import _duplicate_groups
        rows = [task(5, "", stype="daily", at_time="13:30", content="午睡"),
                task(9, "", stype="daily", at_time="13:30", content="午睡")]
        groups = _duplicate_groups(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(sorted(x["id"] for x in groups[0]), [5, 9])


if __name__ == "__main__":
    unittest.main()
