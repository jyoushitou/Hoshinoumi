# ===================== v33.2.1.1 Tool 契约 + native =====================
import asyncio
import unittest

from bot.ports.tool import Tool, ToolSpec
from bot.tools.native import EchoTool, FunctionTool


class TestToolV3321(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(EchoTool(), Tool)

    def test_echo(self):
        out = asyncio.run(EchoTool().invoke("1", {"text": "hi"}))
        self.assertEqual(out["text"], "hi")

    def test_spec(self):
        s = ToolSpec("x", "d", {}, ())
        self.assertEqual(s.name, "x")

    def test_not_wired(self):
        t = FunctionTool(ToolSpec("x"))
        self.assertFalse(asyncio.run(t.invoke("1", {}))["ok"])


if __name__ == "__main__":
    unittest.main()
