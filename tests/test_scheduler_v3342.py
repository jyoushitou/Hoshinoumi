# ===================== v33.4.2.1 调度插件接入 =====================
import unittest

from bot.registry import PluginManifest, PluginRegistry
from bot.scheduling.router import SchedulerRouter


class P: pass


def manifest():
    return PluginManifest(name="fake", author="a", layer="scheduler", version="1.0.0",
                          api_version=1, requires_core=">=33.0.0",
                          capabilities=("scheduler.fake@1",), entrypoint="p:f")


class TestSchedulerRouterV3342(unittest.TestCase):
    def test_native(self):
        self.assertEqual(SchedulerRouter().get("x").__class__.__name__, "AsyncioScheduler")

    def test_plugin(self):
        reg = PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: P())
        r = SchedulerRouter(registry=reg, plugin_factory=lambda rec: rec.factory(None))
        self.assertEqual(r.get("fake").__class__.__name__, "P")


if __name__ == "__main__": unittest.main()
