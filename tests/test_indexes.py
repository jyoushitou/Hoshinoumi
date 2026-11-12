# ===================== v18.14 索引清单 =====================

import sqlite3
import sys
import unittest

sys.path.insert(0, "scripts")

from migrate_indexes import INDEXES, apply, missing  # noqa: E402


class TestIndexes(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        c = self.con.cursor()
        c.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, target_id TEXT, kind TEXT, created_at TEXT)")
        c.execute("CREATE TABLE ai_raw_responses (id INTEGER PRIMARY KEY, target_id TEXT, created_at TEXT)")
        c.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, target_id TEXT, visibility TEXT, valid_until TEXT)")
        self.con.commit()
        self.c = c

    def tearDown(self):
        self.con.close()

    def test_missing_lists_all(self):
        todo = missing(self.c)
        names = {name for _table, name, _cols in todo}
        for items in INDEXES.values():
            for name, _cols in items:
                self.assertIn(name, names)

    def test_apply_idempotent(self):
        first = apply(self.c)
        self.assertEqual(len(first), 3)
        self.assertEqual(missing(self.c), [], "第二次不该再缺")

    def test_missing_table_skipped(self):
        self.c.execute("DROP TABLE ai_raw_responses")
        self.con.commit()
        names = {name for _t, name, _c in missing(self.c)}
        self.assertNotIn("idx_ai_target_time", names)


if __name__ == "__main__":
    unittest.main()
