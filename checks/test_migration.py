# 迁移与数据一致性（checks）：备份 SQL、去重键

import sys
import types
import unittest


def _stub_missing_deps():
    """缺依赖就打个桩（必须在导入 bot 之前调用）"""
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

    try:
        import requests  # noqa: F401
    except ImportError:
        module("requests", Session=lambda: None, get=lambda *a, **k: None,
               post=lambda *a, **k: None)


_stub_missing_deps()


import sys
import types
import unittest
from datetime import datetime
from bot.config import CST
import asyncio
import time
import os
import re
import threading
import json
from bot.ports import ChatModel, Transport  # noqa: E402
from bot.ports.models import ChatRequest, ChatReply  # noqa: E402
from bot.ports.transport import Target, Segment  # noqa: E402
from bot.ai import models as model_mod  # noqa: E402
from bot.ai.chain import FallbackChain  # noqa: E402
from bot.chat.transport import QqTransport  # noqa: E402
from bot.core import state as cfg             # noqa: E402  运行时状态（常量也在里面）
import bot.commands as commands               # noqa: E402
import bot.chat.reply as reply_mod            # noqa: E402
from bot.ai.parse import parse_ai_reply       # noqa: E402
from bot.cmd import registry                  # noqa: E402


class FakeConn:
    """假连接：记录 open/ping 行为"""

    def __init__(self, healthy=True):
        self.open = healthy
        self.pinged = 0
        self.closed = False

    def ping(self, reconnect=False):
        self.pinged += 1
        if not self.open:
            raise RuntimeError("连接已断")

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True
        self.open = False

class FakeCursor:
    def __init__(self, conn):
        self.connection = conn
        self.closed = False

    def close(self):
        self.closed = True

class FakeWS:
    def __init__(self):
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)

    def texts(self):
        """把已发送的报文里的文本段拼出来（命令测试用）"""
        out = []
        for payload in self.sent:
            try:
                d = json.loads(payload)
            except Exception:
                out.append(str(payload))
                continue
            msg = (d.get("params") or {}).get("message") or []
            out.append("".join(
                (seg.get("data") or {}).get("text", "")
                for seg in msg if seg.get("type") == "text"
            ))
        return out

class _FakeCursor:
    """够用的假游标：记录执行过哪些语句"""

    def __init__(self, first_row=None):
        self.first_row = first_row
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((" ".join(str(sql).split()), params))

    def fetchone(self):
        return self.first_row

    def fetchall(self):
        return [self.first_row] if self.first_row else []

    @property
    def connection(self):
        return self

    def commit(self):
        pass

    def verbs(self):
        return [s[0].split()[0].upper() for s in self.statements]

class _FakeRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

class _Resp:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "她回了一句"}}]}

class _Session:
    def post(self, *a, **k):
        return _Resp()

def _at(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=CST)

class TestBackupSqlLiteral(unittest.TestCase):
    """v7 备份脚本：SQL 字面量转义"""

    def setUp(self):
        import os as _os
        import sys as _sys
        scripts = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "scripts")
        if scripts not in _sys.path:
            _sys.path.insert(0, scripts)

    def test_values(self):
        import backup_table as b
        self.assertEqual(b.sql_literal(None), "NULL")
        self.assertEqual(b.sql_literal(3), "3")
        self.assertEqual(b.sql_literal(1.5), "1.5")

    def test_quote_escaped(self):
        import backup_table as b
        s = b.sql_literal("it's ok")
        self.assertTrue(s.startswith("'") and s.endswith("'"))
        self.assertIn("\\'", s)

    def test_bytes_hex(self):
        import backup_table as b
        self.assertEqual(b.sql_literal(b"\x01\x02"), "X'0102'")

    def test_datetime_and_date(self):
        from datetime import date, datetime
        import backup_table as b
        self.assertEqual(b.sql_literal(date(2026, 11, 8)), "'2026-11-08'")
        self.assertIn("2026-11-08 21:30", b.sql_literal(datetime(2026, 11, 8, 21, 30)))

class TestDedupeKey(unittest.TestCase):
    """v7-B14：记忆去重指纹"""

    def setUp(self):
        pass

    def test_punctuation_and_space_ignored(self):
        from bot.infra import dedupe as m
        a = m.dedupe_key("1", "event", "主人 明天要答辩！")
        b = m.dedupe_key("1", "event", "主人明天要答辩")
        self.assertEqual(a, b)

    def test_target_matters(self):
        from bot.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "同一句话"),
            m.dedupe_key("2", "event", "同一句话"),
        )

    def test_kind_matters(self):
        from bot.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "同一句话"),
            m.dedupe_key("1", "life", "同一句话"),
        )

    def test_different_text_differs(self):
        from bot.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "今天加班"),
            m.dedupe_key("1", "event", "今天加班到十点"),
        )

class TestMemoryWriteDedupe(unittest.TestCase):
    """v7-B15：7 天内同键只累加，不新增"""

    def _run(self, existing):
        import bot.infra.repo_memory as rm
        cur = _FakeCursor(existing)
        orig = rm.get_cursor
        rm.get_cursor = lambda: cur
        try:
            rm.add_event_to_db("1", "今天加班", kind="event")
        finally:
            rm.get_cursor = orig
        return cur

    def test_hit_only_updates(self):
        cur = self._run({"id": 7})
        self.assertIn("UPDATE", cur.verbs())
        self.assertNotIn("INSERT", cur.verbs())

    def test_miss_inserts(self):
        cur = self._run(None)
        self.assertIn("INSERT", cur.verbs())
        self.assertIn("DELETE", cur.verbs())  # 插入后按 kind 裁剪

    def test_empty_summary_skipped(self):
        import bot.infra.repo_memory as rm
        cur = _FakeCursor(None)
        orig = rm.get_cursor
        rm.get_cursor = lambda: cur
        try:
            rm.add_event_to_db("1", "")
        finally:
            rm.get_cursor = orig
        self.assertEqual(cur.statements, [])

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
