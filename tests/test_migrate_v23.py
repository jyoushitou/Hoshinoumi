# ===================== v23.1 user_id 迁移 =====================
import shutil
import tempfile
import unittest
from pathlib import Path


class TestMigrateV23(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.path = str(Path(self.tmp) / "m23.db")
        conn.configure(backend="sqlite", sqlite_path=self.path)
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

    def test_adds_user_id_and_backfills_owner(self):
        from scripts import migrate_v23

        self.c.execute(
            "INSERT INTO memories(target_id, kind, summary) VALUES(%s,%s,%s)",
            ("822891053", "event", "旧数据"))
        self.c.connection.commit()

        made = migrate_v23.apply(self.c)
        self.assertIn("memories", made)

        self.c.execute("SELECT user_id FROM memories WHERE target_id=%s", ("822891053",))
        self.assertEqual(self.c.fetchone()["user_id"], "__owner__")

        self.c.execute("PRAGMA table_info(memories)")
        cols = {r["name"] for r in self.c.fetchall()}
        self.assertIn("user_id", cols)

    def test_idempotent(self):
        from scripts import migrate_v23

        first = migrate_v23.apply(self.c)
        second = migrate_v23.apply(self.c)
        self.assertGreater(len(first), 0)
        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
