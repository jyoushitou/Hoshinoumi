# ===================== v35.7.1.1 提醒队列 =====================
import shutil
import tempfile
import unittest
from pathlib import Path


class TestReminders(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "reminders.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_list_and_ack(self):
        from bot.infra import repo_reminders
        rid = repo_reminders.create("10001", "猫咪投喂提醒", source_id=7)
        self.assertTrue(rid)
        rows = repo_reminders.pending()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "猫咪投喂提醒")
        self.assertTrue(repo_reminders.ack(rid, "done"))
        self.assertEqual(repo_reminders.pending(), [])

    def test_later_snoozes_then_reappears(self):
        from bot.infra import repo_reminders
        rid = repo_reminders.create("10001", "喝水")
        self.assertTrue(repo_reminders.ack(rid, "later", snooze_minutes=10))
        self.assertEqual(repo_reminders.pending(), [])
        until = "2000-01-01 00:00:00"
        self.c.execute("UPDATE reminders SET snooze_until=%s WHERE id=%s", (until, rid))
        self.c.connection.commit()
        self.assertEqual(len(repo_reminders.pending()), 1)


if __name__ == "__main__":
    unittest.main()
