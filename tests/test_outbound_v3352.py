# ===================== v33.5.2.1 出站插件接入 =====================
import unittest

from bot.egress.router import TransportRouter
from bot.registry import PluginManifest, PluginRegistry


class P: pass


def manifest():
    return PluginManifest(name="fake", author="a", layer="outbound", version="1.0.0",
                          api_version=1, requires_core=">=33.0.0",
                          capabilities=("transport.fake@1",), entrypoint="p:f")


class TestTransportRouterV3352(unittest.TestCase):
    def test_native(self):
        self.assertEqual(TransportRouter().get("x").__class__.__name__, "WebSocketTransport")

    def test_plugin(self):
        reg = PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: P())
        r = TransportRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.get("fake").__class__.__name__, "P")


if __name__ == "__main__": unittest.main()
