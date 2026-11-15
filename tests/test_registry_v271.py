# ===================== v27.1 注册表骨架 =====================
import unittest

from bot.registry import MasterRegistry, PluginRegistry


class TestPluginRegistry(unittest.TestCase):
    def setUp(self):
        self.r = PluginRegistry()

    def test_register_get_list(self):
        rec = self.r.register("demo", ["tool.demo@1"], lambda ctx: {"ok": True}, priority=5)
        self.assertEqual(rec.name, "demo")
        self.assertIs(self.r.get("tool.demo@1", "demo"), rec)
        self.assertIs(self.r.get("tool.demo@1"), rec)
        self.assertEqual([x.name for x in self.r.list()], ["demo"])
        self.assertEqual(self.r.get("tool.nope"), None)

    def test_duplicate_name(self):
        self.r.register("demo", ["tool.demo@1"], lambda ctx: None)
        with self.assertRaises(ValueError):
            self.r.register("demo", ["tool.other@1"], lambda ctx: None)

    def test_missing_factory(self):
        with self.assertRaises(ValueError):
            self.r.register("x", [], lambda ctx: None)


class TestMasterRegistry(unittest.TestCase):
    def test_static_five_and_order(self):
        m = MasterRegistry()
        self.assertEqual(m.names(), ["command", "events", "life", "ai", "plugin"])
        self.assertFalse(hasattr(m, "register"))
        self.assertEqual(set(m.snapshot()), set(m.names()))
        self.assertEqual(m.snapshot()["plugin"]["count"], 0)
        self.assertTrue(all(m.health().values()))

    def test_plugin_last(self):
        m = MasterRegistry()
        self.assertEqual(m.names()[-1], "plugin")


if __name__ == "__main__":
    unittest.main()
