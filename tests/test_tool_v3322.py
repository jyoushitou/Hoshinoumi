# ===================== v33.2.2.1 工具插件接入 =====================
import asyncio
import unittest

from bot.registry import PluginManifest, PluginRegistry
from bot.tools.router import ToolRouter


class P:
    name = "fake"
    async def invoke(self, user_id, args):
        return {"ok": True, "plugin": True}


def manifest():
    return PluginManifest(
        name="fake", author="a", layer="tools", version="1.0.0",
        api_version=1, requires_core=">=33.0.0",
        capabilities=("tool.fake@1",), entrypoint="p:f",
    )


class TestToolRouterV3322(unittest.TestCase):
    def test_native(self):
        self.assertEqual(ToolRouter().get("echo").__class__.__name__, "EchoTool")

    def test_plugin(self):
        reg = PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: P())
        r = ToolRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.get("fake").__class__.__name__, "P")

    def test_invoke_native(self):
        out = asyncio.run(ToolRouter().invoke("echo", "1", {"text": "x"}))
        self.assertEqual(out["text"], "x")

    def test_invalidate(self):
        r = ToolRouter(); r._cache["x"] = 1; r.invalidate(); self.assertFalse(r._cache)


if __name__ == "__main__":
    unittest.main()
