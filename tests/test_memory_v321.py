# ===================== v32.1 记忆插件权限/错误 =====================
import asyncio
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.memory.router import MemoryRouter
from bot.ports.memory import MemoryItem
from bot.registry import PluginManifest, PluginRegistry


def manifest(name="fake"):
    return PluginManifest(
        name=name, author="a", layer="memory", version="1.0.0",
        api_version=1, requires_core=">=31.0.0",
        capabilities=(f"memory.store.{name}@1",),
        entrypoint="plugin:factory",
    )


class BadStore:
    async def add(self, user_id, item):
        raise RuntimeError("boom")

    async def delete(self, user_id, item_id):
        return None

    async def recent(self, user_id, n):
        return []


class Native:
    async def add(self, user_id, item):
        return "native"


class FakePluginStore:
    def __init__(self):
        self.errors = []

    def get(self, name):
        return types.SimpleNamespace(enabled=True)

    def record_error(self, name, typ, msg):
        self.errors.append((name, typ, msg))


class TestMemoryRouterV321(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "m.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["plugin_permissions"])
        self.c.connection.commit()
        self.reg = PluginRegistry()
        self.reg.register_manifest(manifest(), lambda ctx: BadStore())
        self.ps = FakePluginStore()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def _router(self):
        r = MemoryRouter(registry=self.reg, plugin_store=self.ps)
        r.native = lambda kind, name: Native()
        return r

    def test_default_permission_falls_back_native(self):
        r = self._router()
        self.assertEqual(r.memory_store("fake").__class__.__name__, "Native")

    def test_allowed_error_recorded_and_native(self):
        from bot.plugins.permissions import PermissionStore
        PermissionStore("fake").set("plugin.call", "memory.store.fake@1", 2)
        r = self._router()
        out = asyncio.run(r.add("u", MemoryItem("t", "event", "x"), name="fake"))
        self.assertEqual(out, "native")
        self.assertTrue(self.ps.errors)

    def test_invalidate(self):
        r = self._router()
        r._cache[("store", "fake")] = object()
        r.invalidate("fake")
        self.assertNotIn(("store", "fake"), r._cache)


if __name__ == "__main__":
    unittest.main()
