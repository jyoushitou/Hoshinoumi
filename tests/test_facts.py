# ===================== 事实卡测试（v18.3） =====================

import sys
import types
import unittest
from datetime import datetime, timedelta


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


class TestExtract(unittest.TestCase):
    """规则提取：三档 slot + 极性 + 时效"""

    def setUp(self):
        from bot.life import facts

        self.F = facts
        self.now = datetime(2026, 11, 12, 9, 0)   # 周四

    def test_no_morning_class_tomorrow(self):
        out = self.F.extract("明天没有早八", self.now)
        self.assertEqual(len(out), 1)
        f = out[0]
        self.assertEqual(f["slot"], "课程")
        self.assertEqual(f["value"], "早八")
        self.assertEqual(f["polarity"], 0, "没有 → polarity 0")
        self.assertEqual(f["valid_until"].day, 13)

    def test_has_morning_class(self):
        out = self.F.extract("明天有早八", self.now)
        self.assertEqual(out[0]["polarity"], 1)

    def test_weekday_window(self):
        out = self.F.extract("周四没早八", self.now)
        self.assertEqual(out[0]["day_label"], "周四")

    def test_next_week_whole_week(self):
        out = self.F.extract("下周有考试", self.now)
        f = out[0]
        self.assertEqual(f["day_label"], "下周")
        self.assertEqual(f["valid_from"].isoweekday(), 1, "从下周一开始")
        self.assertEqual(f["valid_until"].isoweekday(), 7, "到下周日结束")

    def test_food_never_expires(self):
        out = self.F.extract("我不吃香菜", self.now)
        self.assertIsNone(out[0]["valid_until"], "饮食禁忌长期有效")

    def test_question_not_stored(self):
        self.assertEqual(self.F.extract("有课吗", self.now), [])
        self.assertEqual(self.F.extract("明天有早八吗？", self.now), [])

    def test_work(self):
        out = self.F.extract("明天要上班", self.now)
        self.assertEqual(out[0]["slot"], "工作")
        self.assertEqual(out[0]["polarity"], 1)

    def test_garbage(self):
        self.assertEqual(self.F.extract("今天天气不错", self.now), [])
        self.assertEqual(self.F.extract("", self.now), [])

    def test_polarity_flip_overwrites(self):
        """「下周有早八」和「没早八」是同一个 slot+value，靠 polarity 区分"""
        a = self.F.extract("明天有早八", self.now)[0]
        b = self.F.extract("明天没早八", self.now)[0]
        self.assertEqual((a["slot"], a["value"]), (b["slot"], b["value"]))
        self.assertNotEqual(a["polarity"], b["polarity"])


class TestPromptBlock(unittest.TestCase):
    """注入格式：带日期语境"""

    def test_block_format(self):
        from bot.life import facts

        orig = facts.active
        facts.active = lambda tid, now=None, limit=10, cursor=None, group=False: [
            {"slot": "课程", "value": "早八", "polarity": 0,
             "valid_until": datetime(2026, 11, 13, 23, 59), "confidence": 0.7},
            {"slot": "饮食", "value": "香菜", "polarity": 0,
             "valid_until": None, "confidence": 0.9},
        ]
        try:
            text = facts.prompt_block("1", now=datetime(2026, 11, 12, 9))
        finally:
            facts.active = orig
        self.assertIn("最近说过的安排", text)
        self.assertIn("11月13日没有早八", text)
        self.assertIn("没有香菜", text)

    def test_empty_returns_blank(self):
        from bot.life import facts

        orig = facts.active
        facts.active = lambda *a, **k: []
        try:
            self.assertEqual(facts.prompt_block("1"), "")
        finally:
            facts.active = orig




class TestPrivacy(unittest.TestCase):
    """v18.4：事实的归属与隐私"""

    def setUp(self):
        from bot.life import facts
        from datetime import datetime

        self.F = facts
        self.now = datetime(2026, 11, 12, 9, 0)

    def test_family_status_is_private(self):
        fs = self.F.extract("我妈住院了", self.now)
        self.assertTrue(fs)
        self.assertEqual(fs[0]["subject"], "妈妈")
        self.assertEqual(fs[0]["visibility"], "private")

    def test_normal_fact_is_group_ok(self):
        fs = self.F.extract("明天没有早八", self.now)
        self.assertEqual(fs[0]["subject"], "自己")
        self.assertEqual(fs[0]["visibility"], "group_ok")

    def test_secret_marker(self):
        self.assertEqual(self.F.visibility_of("这个别告诉别人", "自己"), "secret")

    def test_group_filter_drops_private(self):
        rows = [
            {"slot": "课程", "value": "早八", "polarity": 0,
             "visibility": "group_ok", "valid_until": None},
            {"slot": "近况", "value": "住院", "polarity": 1,
             "visibility": "private", "valid_until": None},
        ]
        orig = self.F.active
        self.F.active = lambda tid, now=None, limit=10, cursor=None, group=False: [
            r for r in rows if (not group) or r["visibility"] == "group_ok"]
        try:
            priv = self.F.prompt_block("1", group=False)
            pub = self.F.prompt_block("1", group=True)
        finally:
            self.F.active = orig
        self.assertIn("住院", priv, "私聊应该看得到")
        self.assertNotIn("住院", pub, "群里绝不该出现")
        self.assertIn("岔开", pub, "群聊要带「装不知道」提示")


if __name__ == "__main__":
    unittest.main()
