# ===================== v33.1.2.1 通道插件接入 =====================
import sys
import types
import unittest

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.channels.router import ChannelRouter
from bot.registry import PluginManifest, PluginRegistry


class P:
    name = "fake"


def manifest():
    return PluginManifest(
        name="fake", author="a", layer="channels", version="1.0.0",
        api_version=1, requires_core=">=33.0.0",
        capabilities=("channel.fake@1",), entrypoint="p:f",
    )


class TestChannelRouterV3312(unittest.TestCase):
    def test_native(self):
        self.assertEqual(ChannelRouter().get("nope").__class__.__name__, "QQChannel")

    def test_plugin(self):
        reg = PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: P())
        r = ChannelRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.get("fake").__class__.__name__, "P")

    def test_invalidate(self):
        r = ChannelRouter(); r._cache["x"] = object(); r.invalidate()
        self.assertEqual(r._cache, {})


if __name__ == "__main__":
    unittest.main()
