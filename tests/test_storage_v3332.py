# ===================== v33.3.2.1 存储插件接入 =====================
import unittest

from bot.registry import PluginManifest, PluginRegistry
from bot.storage.router import StorageRouter


class P: pass


def manifest():
    return PluginManifest(name="fake", author="a", layer="storage", version="1.0.0",
                          api_version=1, requires_core=">=33.0.0",
                          capabilities=("storage.backend.fake@1",), entrypoint="p:f")


class TestStorageRouterV3332(unittest.TestCase):
    def test_native(self):
        self.assertEqual(StorageRouter().get("storage.backend", "sql").__class__.__name__, "SQLStorage")

    def test_plugin(self):
        reg = PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: P())
        r = StorageRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.get("storage.backend", "fake").__class__.__name__, "P")

    def test_invalidate(self):
        r = StorageRouter(); r._cache[("storage.backend", "x")] = 1; r.invalidate("x")
        self.assertEqual(r._cache, {})


if __name__ == "__main__": unittest.main()
