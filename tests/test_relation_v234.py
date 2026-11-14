# ===================== v23.4 亲密度下降/修复 =====================
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _stub():
    try:
        import jieba  # noqa: F401
    except ImportError:
        m = types.ModuleType("jieba")
        m.lcut = lambda s: list(s)
        sys.modules["jieba"] = m


_stub()


class TestRelationV234(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        from scripts import migrate_v23
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "rel.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        migrate_v23.apply(self.c)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_range_and_severe_jump(self):
        from bot.life import relation
        self.assertEqual(relation.apply_delta("u_a", -2.0, "背叛", "severe"), -1.0)
        self.assertEqual(relation.apply_delta("u_a", 2.0, "修复", "repair"), 1.0)

    def test_negative_tiers(self):
        from bot.life import relation
        self.assertEqual(relation.tier_of(-0.1)[0], "冷淡")
        self.assertEqual(relation.tier_of(-0.4)[0], "厌恶")
        self.assertEqual(relation.tier_of(-0.8)[0], "破裂")
        self.assertEqual(relation.tier_of(0.0)[0], "归零")

    def test_negative_no_normal_gain_and_repair(self):
        from bot.life import relation
        relation.apply_delta("u_a", -0.2, "冷战", "major")
        before = relation.get("u_a")
        self.assertEqual(relation.bump("u_a"), before)
        after = relation.repair("u_a")
        self.assertAlmostEqual(after, before + 0.02, places=3)

    def test_reply_probability_floor(self):
        from bot.life import relation
        relation.apply_delta("u_a", -0.6, "破裂", "severe")
        self.assertEqual(relation.reply_probability("u_a"), 0.01)
        self.assertTrue(relation.should_answer_private("u_a", "对不起"))

    def test_events_are_user_scoped(self):
        from bot.life import relation
        relation.apply_delta("u_a", -0.3, "公开羞辱", "severe", user_id="u_a")
        relation.apply_delta("u_b", -0.1, "小摩擦", "minor", user_id="u_b")
        a = relation.recent_events("u_a", user_id="u_a")
        b = relation.recent_events("u_b", user_id="u_b")
        self.assertTrue(a and "公开羞辱" in a[0]["reason"])
        self.assertTrue(b and "小摩擦" in b[0]["reason"])
        self.assertFalse(any("公开羞辱" in x["reason"] for x in b))


if __name__ == "__main__":
    unittest.main()
