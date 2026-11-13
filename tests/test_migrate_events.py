# ===================== v18.17 events → memories 迁移 =====================

import sqlite3
import sys
import unittest

sys.path.insert(0, "scripts")

from migrate_v18 import migrate_events  # noqa: E402


class TestMigrateEvents(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        c = self.con.cursor()
        c.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id TEXT, kind TEXT, summary TEXT, tags TEXT,
                importance INTEGER DEFAULT 3, weight REAL DEFAULT 0.5,
                tier TEXT DEFAULT 'medium', source TEXT DEFAULT 'chat',
                dedupe_key TEXT, due_date TEXT, last_seen TEXT,
                hit_count INTEGER DEFAULT 0, created_at TEXT, deleted_at TEXT,
                UNIQUE(target_id, dedupe_key)
            )
        """)
        c.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id TEXT, event_summary TEXT, tags TEXT, kind TEXT,
                dedupe_key TEXT, importance INTEGER, due_date TEXT,
                last_seen TEXT, hit_count INTEGER DEFAULT 0,
                created_at TEXT, deleted_at TEXT
            )
        """)
        c.execute("INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, "
                  "importance, created_at) VALUES('1','妈妈住院了','家事','event','k1',3,'2026-11-01')")
        c.execute("INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, "
                  "importance, created_at) VALUES('__self__','{\"due\":1}','','agenda',NULL,3,'2026-11-02')")
        self.con.commit()
        self.c = c

    def tearDown(self):
        self.con.close()

    def test_old_events_without_deleted_at(self):
        """v17.4.1 的老库没有 deleted_at，迁移不能因此失败"""
        self.c.execute("ALTER TABLE events DROP COLUMN deleted_at")
        self.con.commit()
        self.assertEqual(migrate_events(self.c), 0)
        self.c.execute("SELECT COUNT(*) AS n FROM memories")
        self.assertEqual(self.c.fetchone()["n"], 2)

    def test_copy_and_drop_view(self):
        rc = migrate_events(self.c)
        self.assertEqual(rc, 0)
        self.c.execute("SELECT COUNT(*) AS n FROM memories")
        self.assertEqual(self.c.fetchone()["n"], 2)
        self.c.execute("SELECT summary, kind FROM memories ORDER BY id")
        rows = self.c.fetchall()
        self.assertEqual(rows[0]["summary"], "妈妈住院了")
        self.assertEqual(rows[1]["kind"], "agenda")
        # v19.5：events 名字不再存在（基表已改名，兼容视图已删）
        self.c.execute("SELECT name FROM sqlite_master WHERE name='events'")
        self.assertIsNone(self.c.fetchone())
        # 重复跑必须安全
        self.assertEqual(migrate_events(self.c), 0)
        self.c.execute("SELECT COUNT(*) AS n FROM memories")
        self.assertEqual(self.c.fetchone()["n"], 2)


if __name__ == "__main__":
    unittest.main()
