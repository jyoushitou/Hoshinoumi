# ===================== v32.2 记忆插件停用回落 =====================
import sys
import types
import unittest

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.memory.router import MemoryRouter
from bot.registry import PluginManifest, PluginRegistry


def manifest(name="fake"):
    return PluginManifest(
        name=name, author="a", layer="memory", version="1.0.0",
        api_version=1, requires_core=">=31.0.0",
        capabilities=(f"memory.store.{name}@1",),
        entrypoint="plugin:factory",
    )


class P:
    pass


class N:
    pass


class TestDisable(unittest.TestCase):
    def _router(self, enabled):
        reg = PluginRegistry()
        reg.register_manifest(manifest(), lambda ctx: P())
        ps = types.SimpleNamespace(
            get=lambda name: types.SimpleNamespace(enabled=enabled),
            record_error=lambda *a: None,
        )
        r = MemoryRouter(registry=reg, plugin_store=ps,
                         plugin_factory=lambda rec: rec.factory(None))
        r.native = lambda kind, name: N()
        return r

    def test_disabled_falls_back(self):
        self.assertEqual(self._router(False).memory_store("fake").__class__.__name__, "N")

    def test_enabled_uses_plugin(self):
        self.assertEqual(self._router(True).memory_store("fake").__class__.__name__, "P")


if __name__ == "__main__":
    unittest.main()
