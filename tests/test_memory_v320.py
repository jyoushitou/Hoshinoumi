# ===================== v32.0 记忆插件接入点 =====================
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


def manifest(name="fake", kind="store"):
    return PluginManifest(
        name=name, author="a", layer="memory", version="1.0.0",
        api_version=1, requires_core=">=31.0.0",
        capabilities=(f"memory.{kind}.{name}@1",),
        entrypoint="plugin:factory",
    )


class FakeStore:
    async def add(self, user_id, item):
        return "x"

    async def delete(self, user_id, item_id):
        return None

    async def recent(self, user_id, n):
        return []


class TestMemoryRouterV320(unittest.TestCase):
    def test_plugin_store_selected(self):
        reg = PluginRegistry()
        reg.register_manifest(manifest(), lambda ctx: FakeStore())
        r = MemoryRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.memory_store("fake").__class__.__name__, "FakeStore")

    def test_native_fallback(self):
        r = MemoryRouter(registry=PluginRegistry())
        self.assertEqual(r.memory_store("sql").__class__.__name__, "SQLMemoryStore")
        self.assertEqual(r.retriever("bm25").__class__.__name__, "BM25Retriever")

    def test_invalidate(self):
        r = MemoryRouter(registry=PluginRegistry())
        r._cache[("store", "fake")] = object()
        r.invalidate("fake")
        self.assertNotIn(("store", "fake"), r._cache)


if __name__ == "__main__":
    unittest.main()
