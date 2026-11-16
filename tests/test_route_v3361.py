# ===================== v33.6.1.1 RouteRegistry + native =====================
import unittest

from bot.ports.route import Candidate, RouteKey, RouteRegistry
from bot.routing.native import NativeRouteRegistry


class TestRouteV3361(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(NativeRouteRegistry(), RouteRegistry)

    def test_defaults(self):
        r = NativeRouteRegistry()
        for layer, name in (("model", "deepseek"), ("memory", "bm25"), ("channel", "qq")):
            c = r.resolve(RouteKey(layer))
            self.assertEqual(c.origin, "native")
            self.assertEqual(c.name, name)

    def test_candidates(self):
        self.assertEqual(len(NativeRouteRegistry().candidates(RouteKey("tool"))), 1)


if __name__ == "__main__": unittest.main()
