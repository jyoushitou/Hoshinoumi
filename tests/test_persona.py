# 角色卡：加载、切换

import sys
import types
import unittest


def _stub_missing_deps():
    """缺依赖就打个桩（必须在导入 botv 之前调用）"""
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
from botv.config import CST
import asyncio
import time
import os
import re
import threading
import json
from botv.ports import ChatModel, Transport  # noqa: E402
from botv.ports.models import ChatRequest, ChatReply  # noqa: E402
from botv.ports.transport import Target, Segment  # noqa: E402
from botv.ai import models as model_mod  # noqa: E402
from botv.ai.chain import FallbackChain  # noqa: E402
from botv.chat.transport import QqTransport  # noqa: E402
from botv.core import state as cfg             # noqa: E402  运行时状态（常量也在里面）
import botv.commands as commands               # noqa: E402
import botv.chat.reply as reply_mod            # noqa: E402
from botv.ai.parse import parse_ai_reply       # noqa: E402
from botv.cmd import registry                  # noqa: E402


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

class TestPersonaCard(unittest.TestCase):
    """v14-A1/A2：角色卡加载与回退"""

    def test_card_loaded(self):
        from botv.ai.persona_loader import card_dir, describe
        self.assertIsNotNone(card_dir())
        self.assertEqual(describe(), "nao")

    def test_prompt_from_card(self):
        from botv.ai.persona_loader import load_text
        text = load_text("prompt.txt")
        self.assertTrue(text)
        self.assertIn("{now}", text, "占位符必须保留")

    def test_life_from_card(self):
        from botv.ai.persona_loader import load_life
        pools = load_life()
        self.assertTrue(pools)
        self.assertGreaterEqual(sum(len(t) for _w, t in pools), 100)

    def test_state_from_card(self):
        from botv.ai.persona_loader import load_state_base
        base = load_state_base()
        self.assertIn("mood", base)

    def test_missing_file_returns_none(self):
        from botv.ai.persona_loader import load_text
        self.assertIsNone(load_text("no_such_file.txt"))

    def test_env_selects_card(self):
        import os
        from botv.ai import persona_loader as L
        old = os.environ.get("NAO_PERSONA")
        os.environ["NAO_PERSONA"] = "not_exist_card"
        try:
            self.assertEqual(L.describe(), "nao", "找不到就回退默认卡")
        finally:
            if old is None:
                os.environ.pop("NAO_PERSONA", None)
            else:
                os.environ["NAO_PERSONA"] = old

    def test_prompt_uses_card(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        text = get_system_prompt()
        self.assertIn("友利奈绪", text)

class TestPersonaSwitch(unittest.TestCase):
    """v14-A3：多角色切换"""

    def setUp(self):
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.persona_name = ""

    def tearDown(self):
        self.cfg.persona_name = ""

    def test_lists_cards(self):
        from botv.ai.persona_loader import available_cards
        self.assertIn("nao", available_cards())

    def test_default_active(self):
        from botv.ai.persona_loader import active_name
        self.assertEqual(active_name(), "nao")

    def test_runtime_switch(self):
        import os
        from botv.ai import persona_loader as L
        os.makedirs(os.path.join(L.CARD_ROOT, "testcard"), exist_ok=True)
        try:
            self.cfg.persona_name = "testcard"
            self.assertEqual(L.active_name(), "testcard")
        finally:
            self.cfg.persona_name = ""
            import shutil
            shutil.rmtree(os.path.join(L.CARD_ROOT, "testcard"), ignore_errors=True)

    def test_unknown_falls_back(self):
        from botv.ai import persona_loader as L
        self.cfg.persona_name = "根本没有这张卡"
        self.assertEqual(L.active_name(), "nao")

    def test_reload_supplement(self):
        from botv.ai.prompt import reload_personality_supplement
        import botv.ai.prompt as P
        reload_personality_supplement()
        self.assertTrue(P.PERSONALITY_SUPPLEMENT)

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
