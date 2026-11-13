# ===================== 记忆分量判定测试（v18.0 U2） =====================

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


class TestClassify(unittest.TestCase):
    """三档判定：规则优先，默认轻"""

    def setUp(self):
        from bot.memory import weight

        self.W = weight

    def test_heavy_family_illness(self):
        for text in ("我妈住院了", "我爷爷去世了", "确诊了", "要手术"):
            tier, w, _ = self.W.classify(text)
            self.assertEqual(tier, "heavy", text)
            self.assertEqual(w, 0.9)

    def test_heavy_relationship(self):
        for text in ("我们分手了", "要结婚了", "她怀孕了"):
            self.assertEqual(self.W.classify(text)[0], "heavy", text)

    def test_medium_work_study(self):
        for text in ("明天面试", "考研压力好大", "加班到十点"):
            self.assertEqual(self.W.classify(text)[0], "medium", text)

    def test_medium_promise(self):
        self.assertEqual(self.W.classify("答应周末去爬山")[0], "medium")

    def test_light_default(self):
        for text in ("今天吃了碗面", "天气不错", "好困"):
            tier, w, _ = self.W.classify(text)
            self.assertEqual(tier, "light", text)
            self.assertEqual(w, 0.3)

    def test_empty(self):
        self.assertEqual(self.W.classify("")[0], "light")
        self.assertEqual(self.W.classify(None)[0], "light")

    def test_punctuation_ignored(self):
        self.assertEqual(self.W.classify("我，妈。住 院 了")[0], "heavy")

    def test_heavy_beats_medium(self):
        """同时含「加班」和「住院」→ 重"""
        self.assertEqual(self.W.classify("加班时听说我妈住院了")[0], "heavy")

    def test_hit_word_returned(self):
        tier, w, hit = self.W.classify("我妈住院了")
        self.assertEqual(hit, "住院")

    def test_bump_up_only(self):
        self.assertEqual(self.W.bump("light", "medium")[0], "medium")
        self.assertEqual(self.W.bump("heavy", "light")[0], "heavy")
        self.assertEqual(self.W.bump("medium", "medium")[0], "medium")

    def test_bump_unknown_values(self):
        self.assertEqual(self.W.bump("bogus", "heavy")[0], "heavy")
        self.assertEqual(self.W.bump("bogus", "bogus")[0], "light")

    def test_describe(self):
        self.assertIn("长期", self.W.describe("heavy"))
        self.assertIn("90", self.W.describe("medium"))
        self.assertIn("7", self.W.describe("light"))


if __name__ == "__main__":
    unittest.main()
