# ===================== v33.6.2.1 默认链路候选 + !route =====================
import unittest

from bot.ports.route import Candidate, RouteKey
from bot.registry import PluginManifest, PluginRegistry
from bot.routing.router import RouteRouter


def manifest():
    return PluginManifest(name="fake", author="a", layer="routes", version="1.0.0",
                          api_version=1, requires_core=">=33.0.0",
                          capabilities=("route.model.fake@1",), entrypoint="p:f")


class TestRouteV3362(unittest.TestCase):
    def test_plugin_candidate_native_still_default(self):
        reg=PluginRegistry(); reg.register_manifest(manifest(), lambda ctx: object())
        r=RouteRouter(registry=reg)
        self.assertEqual(r.resolve(RouteKey("model")).origin,"native")
        cands=r.candidates(RouteKey("model"))
        self.assertTrue(any(c.origin=="plugin" for c in cands))

    def test_explain(self):
        from bot.cmd.route_cmd import cmd_route
        from bot.cmd.registry import CommandContext
        import asyncio
        ctx=CommandContext(parts=["route","model"],uid="1",ws=None,is_group=False,gid=0)
        out=asyncio.run(cmd_route(ctx))
        self.assertIn("默认固定 native",out)


if __name__=="__main__": unittest.main()
