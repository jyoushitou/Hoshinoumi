# ===================== v30.1 模型插件权限/错误/失效 =====================
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

from bot.ai.model_router import ModelRouter
from bot.plugins.store import PluginStore
from bot.ports.models import ModelReply, ModelRequest
from bot.registry import PluginManifest, PluginRegistry
from scripts import migrate_v28


def manifest(name="fake"):
    return PluginManifest(
        name=name, author="a", layer="models", version="1.0.0",
        api_version=1, requires_core=">=30.0.0",
        capabilities=(f"model.{name}@1",), entrypoint="plugin:factory",
    )


class BadProvider:
    async def complete(self, req):
        raise RuntimeError("boom")


class NativeFake:
    async def complete(self, req):
        return ModelReply(text="native", model="native")


class TestModelRouterV301(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "m.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        self.c.connection.commit()
        migrate_v28.apply(self.c)
        self.store = PluginStore()
        self.reg = PluginRegistry()
        self.reg.register_manifest(manifest(), lambda ctx: BadProvider())

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def _router(self):
        r = ModelRouter(registry=self.reg, store=self.store)
        r.native = lambda name: NativeFake()
        return r

    def test_default_permission_falls_back(self):
        r = self._router()
        out = asyncio.run(r.complete("fake", ModelRequest(messages=[])))
        self.assertEqual(out.text, "native")

    def test_allowed_plugin_error_recorded_and_fallback(self):
        from bot.plugins.permissions import PermissionStore
        PermissionStore("fake").set("plugin.call", "model.fake@1", 2)
        r = self._router()
        out = asyncio.run(r.complete("fake", ModelRequest(messages=[])))
        self.assertEqual(out.text, "native")
        self.assertTrue(self.store.errors("fake"))

    def test_invalidate_provider_cache(self):
        r = self._router()
        r._cache["fake"] = BadProvider()
        r.invalidate("fake")
        self.assertNotIn("fake", r._cache)


if __name__ == "__main__":
    unittest.main()
