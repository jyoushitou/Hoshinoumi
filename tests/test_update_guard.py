# ===================== v25.4 热更新准入 =====================
import unittest


class TestUpdateGuard(unittest.TestCase):
    def test_normal_allowed(self):
        from bot.core import update_guard as G
        ok, why = G.check({"version": "25.4.0", "requires_restart": False,
                           "requires_schema": False, "schema_version": 29}, 29)
        self.assertTrue(ok, why)

    def test_restart_refused(self):
        from bot.core import update_guard as G
        ok, why = G.check({"version": "25.4.0", "requires_restart": True}, 29)
        self.assertFalse(ok)
        self.assertIn("重启", why)

    def test_schema_refused(self):
        from bot.core import update_guard as G
        ok, why = G.check({"version": "25.4.0", "requires_schema": True}, 29)
        self.assertFalse(ok)
        self.assertIn("迁移", why)

    def test_schema_mismatch_refused(self):
        from bot.core import update_guard as G
        ok, why = G.check({"version": "25.4.0", "schema_version": 30}, 29)
        self.assertFalse(ok)
        self.assertIn("30", why)

    def test_missing_manifest_refused(self):
        from bot.core import update_guard as G
        ok, why = G.check({}, 29)
        self.assertFalse(ok)
        self.assertIn("version", why)

    def test_status_text(self):
        from bot.core import update_guard as G
        text = G.status_text({"version": "25.4.0"}, False, "需要重启")
        self.assertIn("拒绝热更新", text)
        self.assertIn("维护窗口", text)


if __name__ == "__main__":
    unittest.main()
