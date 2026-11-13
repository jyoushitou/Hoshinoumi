# ===================== v18.12 突然想起 =====================

import sys
import types
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch


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


class TestRecall(unittest.TestCase):
    def setUp(self):
        from bot.life import recall
        from bot.core import state as cfg

        self.R = recall
        self.cfg = cfg
        cfg.recall_day = None
        self.now = datetime(2026, 11, 12, 20, 0)

    def _rows(self, days_old=10):
        return [{"summary": "妈妈住院了", "weight": 0.9,
                 "created_at": (self.now - timedelta(days=days_old)).strftime("%Y-%m-%d %H:%M:%S"),
                 "last_seen": None}]

    def test_pick_once_per_day(self):
        with patch("bot.life.state.current", return_value={"mood": 0.1}), \
                patch("bot.infra.repo_memory.load_heavy_memories", return_value=self._rows()):
            first = self.R.pick(now=self.now)
            second = self.R.pick(now=self.now)
        self.assertIsNotNone(first)
        self.assertIn("妈妈住院了", first["prompt"])
        self.assertIsNone(second, "一天只提一次")

    def test_skip_when_sad(self):
        with patch("bot.life.state.current", return_value={"mood": -0.8}), \
                patch("bot.infra.repo_memory.load_heavy_memories", return_value=self._rows()):
            self.assertIsNone(self.R.pick(now=self.now))

    def test_skip_recently_mentioned(self):
        rows = self._rows()
        rows[0]["last_seen"] = (self.now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with patch("bot.life.state.current", return_value={"mood": 0.1}), \
                patch("bot.infra.repo_memory.load_heavy_memories", return_value=rows):
            self.assertIsNone(self.R.pick(now=self.now))


if __name__ == "__main__":
    unittest.main()
