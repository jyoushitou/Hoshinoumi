# ===================== v30.2 停用/回落回归 =====================
import sys
import types
import unittest
from types import SimpleNamespace

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.ai.model_router import ModelRouter
from bot.ports.models import ModelReply
from bot.registry import PluginManifest, PluginRegistry


def manifest(name="fake"):
    return PluginManifest(
        name=name, author="a", layer="models", version="1.0.0",
        api_version=1, requires_core=">=30.0.0",
        capabilities=(f"model.{name}@1",), entrypoint="plugin:factory",
    )


class P:
    async def complete(self, req):
        return ModelReply(text="plugin", model="fake")


class N:
    async def complete(self, req):
        return ModelReply(text="native", model="native")


class TestDisableFallback(unittest.TestCase):
    def _router(self, enabled):
        reg = PluginRegistry()
        reg.register_manifest(manifest(), lambda ctx: P())
        store = SimpleNamespace(get=lambda name: SimpleNamespace(enabled=enabled))
        r = ModelRouter(registry=reg, store=store,
                        plugin_factory=lambda rec: rec.factory(None))
        r.native = lambda name: N()
        return r

    def test_disabled_falls_back_native(self):
        self.assertEqual(self._router(False).provider("fake").__class__.__name__, "N")

    def test_enabled_uses_plugin(self):
        self.assertEqual(self._router(True).provider("fake").__class__.__name__, "P")


if __name__ == "__main__":
    unittest.main()
