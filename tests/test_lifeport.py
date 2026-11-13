# ===================== 生活端口测试（v17.15 债二） =====================

import ast
import io
import sys
import types
import unittest


def _stub_missing_deps():
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None

    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)


_stub_missing_deps()


class TestLifePort(unittest.TestCase):
    """端口：注册/注销、缺实现给默认值、未知名字直接报错"""

    def setUp(self):
        from bot.core import lifeport

        self.LP = lifeport
        self._saved = dict(lifeport._impl)
        lifeport._impl.clear()

    def tearDown(self):
        self.LP._impl.clear()
        self.LP._impl.update(self._saved)

    def test_missing_returns_default(self):
        self.assertEqual(self.LP.life.state_line("1"), "")
        self.assertEqual(self.LP.life.habit_line("1"), "")
        # touch_talk 默认是 None（不是可调用对象），调用方要容忍
        self.assertIsNone(self.LP.life.touch_talk("1"))

    def test_register_and_call(self):
        self.LP.register("state_line", lambda tid: "她有点累")
        self.assertEqual(self.LP.life.state_line("1"), "她有点累")
        self.assertIn("state_line", self.LP.available())

    def test_unregister(self):
        self.LP.register("reading_line", lambda tid: "在看小说")
        self.LP.unregister("reading_line")
        self.assertEqual(self.LP.life.reading_line("1"), "")

    def test_unknown_name_rejected(self):
        with self.assertRaises(KeyError):
            self.LP.register("not_a_thing", lambda: None)

    def test_unknown_attribute(self):
        with self.assertRaises(AttributeError):
            self.LP.life.no_such

    def test_specific_defaults_keep_type(self):
        """touch_talk 默认返回 None 的可调用对象，不能返回空串"""
        fn = self.LP.life.touch_talk
        self.assertIsNone(fn("1"))

    def test_bridge_registers_all(self):
        from bot.app.life_bridge import setup_life_bridge
        names = setup_life_bridge()
        self.assertGreaterEqual(len(names), 10)
        self.assertIn("state_line", names)
        self.assertIn("condense", names)


class TestAiNoLifeImport(unittest.TestCase):
    """ai 层顶层不能再 import life"""

    def test_no_top_level_life_import(self):
        from bot.ai import client

        with io.open(client.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        bad = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.split(".")[-1] == "life" or ".life." in mod:
                    bad.append(mod)
        self.assertEqual(bad, [], f"顶层仍 import life：{bad}")

    def test_client_uses_port(self):
        from bot.ai import client

        self.assertTrue(hasattr(client, "life"))


if __name__ == "__main__":
    unittest.main()
