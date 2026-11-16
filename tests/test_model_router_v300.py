# ===================== v30.0 模型插件接入点 =====================
import asyncio
import sys
import types
import unittest

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.ai.model_router import ModelRouter
from bot.ports.models import ModelReply, ModelRequest
from bot.registry import PluginManifest, PluginRegistry


def manifest(name="fake"):
    return PluginManifest(
        name=name, author="a", layer="models", version="1.0.0",
        api_version=1, requires_core=">=29.0.0",
        capabilities=(f"model.{name}@1",), entrypoint="plugin:factory",
    )


class FakeProvider:
    name = "fake"

    def capabilities(self):
        return {"text"}

    async def complete(self, req):
        return ModelReply(text="plugin", model="fake")


class TestModelRouterV300(unittest.TestCase):
    def test_plugin_selected(self):
        reg = PluginRegistry()
        reg.register_manifest(manifest(), lambda ctx: FakeProvider())
        r = ModelRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        out = asyncio.run(r.complete("fake", ModelRequest(messages=[]), fallback=False))
        self.assertEqual(out.text, "plugin")

    def test_native_when_missing(self):
        r = ModelRouter(registry=PluginRegistry())
        self.assertEqual(type(r.native("deepseek")).__name__, "DeepSeekProvider")
        self.assertIsNone(r.native("missing"))

    def test_invalidate(self):
        r = ModelRouter(registry=PluginRegistry())
        r._cache["x"] = object()
        r.invalidate("x")
        self.assertNotIn("x", r._cache)


if __name__ == "__main__":
    unittest.main()
