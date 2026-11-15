# ===================== v27.3 快照/健康/核心不注册 =====================
import unittest

from bot.registry import (
    PluginManifest, PluginRegistry, get_master, health, reset_master, snapshot,
)


def manifest(name="demo", cap="tool.demo@1"):
    return PluginManifest(
        name=name, author="author", layer="tools", version="1.0.0",
        api_version=1, requires_core=">=27.0.0", capabilities=(cap,),
        entrypoint="plugin:factory", auto_start=False, priority=1,
    )


class TestRegistryStatus(unittest.TestCase):
    def setUp(self):
        reset_master()

    def test_snapshot_has_five_registries(self):
        data = snapshot()
        self.assertEqual(list(data), ["command", "events", "life", "ai", "plugin"])
        self.assertEqual(data["plugin"]["count"], 0)
        self.assertTrue(all(health().values()))

    def test_core_native_not_registered(self):
        m = get_master()
        self.assertEqual(m.plugin.list(), [])
        self.assertEqual(m.snapshot()["plugin"]["items"], [])

    def test_third_party_visible(self):
        reg = PluginRegistry()
        reg.register_manifest(manifest(), lambda ctx: None)
        self.assertEqual(len(reg.list()), 1)
        self.assertEqual(reg.list()[0].name, "demo")


if __name__ == "__main__":
    unittest.main()
