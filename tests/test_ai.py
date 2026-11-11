# 模型与感官：反 AI 腔、超时、视觉、语音、工具

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

class TestASR(unittest.TestCase):
    """v11-A14：语音转文字（不可用时安静降级）"""

    def test_filename_guess(self):
        from botv.speech.asr import _filename_for
        self.assertTrue(_filename_for("https://x/a.mp3").endswith(".mp3"))
        self.assertTrue(_filename_for("https://x/a.amr").endswith(".amr"))
        self.assertTrue(_filename_for("").endswith(".mp3"))

    def test_no_key_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = ""
        try:
            self.assertIsNone(asyncio.run(transcribe(b"fake-audio")))
        finally:
            cfg.DS_API_KEY = orig

    def test_oversized_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe, MAX_BYTES
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = "k"
        try:
            self.assertIsNone(asyncio.run(transcribe(b"x" * (MAX_BYTES + 1))))
        finally:
            cfg.DS_API_KEY = orig

    def test_empty_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe
        self.assertIsNone(asyncio.run(transcribe(b"")))

class TestAntiAIStyle(unittest.TestCase):
    """v6-A23：反 AI 腔清单必须进 prompt"""

    def setUp(self):
        cfg.CODE_MODE = False

    def test_prompt_has_style_block(self):
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        self.assertIn("别像 AI", p)
        self.assertIn("总而言之", p)
        self.assertIn("我理解你的感受", p)

    def test_code_mode_has_hint(self):
        from botv.ai.prompt import get_system_prompt
        cfg.CODE_MODE = True
        try:
            p = get_system_prompt()
        finally:
            cfg.CODE_MODE = False
        self.assertIn("总而言之", p)

class TestFewShot(unittest.TestCase):
    """v6-A22：示例对话要进 prompt，且不带 AI 腔"""

    def setUp(self):
        cfg.CODE_MODE = False

    def test_prompt_has_examples(self):
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        self.assertIn("她说话的样子", p)
        self.assertIn("主人：", p)
        self.assertIn("奈绪：", p)

    def test_examples_show_optional_action(self):
        """示例里要有一条没有动作的，告诉模型动作可省"""
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        block = p.split("【她说话的样子】")[1].split("回复必须")[0]
        lines = [l for l in block.split("\n") if l.startswith("奈绪：")]
        self.assertTrue(any("（" not in l for l in lines), "至少要有一条没动作的示例")

class TestImagePath(unittest.TestCase):
    """F4：图片路径解析不依赖当前工作目录"""

    def test_empty(self):
        from botv.utils import resolve_image_path
        self.assertIsNone(resolve_image_path(""))
        self.assertIsNone(resolve_image_path(None))

    def test_relative_resolved_from_project_root(self):
        import os
        from botv.utils import resolve_image_path
        p = resolve_image_path("botv/__init__.py")  # 项目根下确定存在的文件（大小写无关）
        self.assertIsNotNone(p)
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(os.path.exists(p))

    def test_missing_returns_none(self):
        from botv.utils import resolve_image_path
        self.assertIsNone(resolve_image_path("no/such/file.jpg"))

    def test_absolute_existing(self):
        import os
        from botv.utils import resolve_image_path
        p = resolve_image_path(os.path.abspath("botv/__init__.py"))
        self.assertIsNotNone(p)

class TestReferer(unittest.TestCase):
    """v8-FIX：防盗链 Referer 跟图片域名走"""

    def test_own_domain(self):
        from botv.utils import referer_for
        self.assertEqual(referer_for("https://p6.itc.cn/q_70/a.jpg"), "https://p6.itc.cn/")
        self.assertEqual(referer_for("http://file.alapi.cn/image/x.jpg"), "http://file.alapi.cn/")

    def test_fallback(self):
        from botv.utils import referer_for
        self.assertEqual(referer_for(""), "https://www.google.com/")
        self.assertEqual(referer_for("not-a-url"), "https://www.google.com/")

class TestSessionReuse(unittest.TestCase):
    """v8-E27：线程本地会话复用"""

    def test_same_thread_same_session(self):
        from botv.core.http import get_http_session
        a = get_http_session()
        b = get_http_session()
        self.assertIs(a, b)

    def test_different_thread_different_session(self):
        import threading
        from botv.core.http import get_http_session
        main_session = get_http_session()
        box = {}

        def worker():
            box["s"] = get_http_session()

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        self.assertIsNot(box["s"], main_session)

class TestTimeoutTiers(unittest.TestCase):
    """v8-E28：超时分级"""

    def test_chat_vs_long(self):
        from botv.ai.client import _timeout_for
        from botv.core.constants import CHAT_TIMEOUT, LONG_TIMEOUT
        self.assertEqual(_timeout_for(200), CHAT_TIMEOUT)
        self.assertEqual(_timeout_for(1500), LONG_TIMEOUT)
        self.assertEqual(_timeout_for(None), CHAT_TIMEOUT)

class TestTone(unittest.TestCase):
    """v6-A20：按时段给语气提示"""

    def test_bands(self):
        from datetime import datetime
        from botv.chat.timing import tone_hint
        from botv.config import CST
        self.assertIn("困", tone_hint(datetime(2026, 1, 1, 2, tzinfo=CST)))
        self.assertIn("刚醒", tone_hint(datetime(2026, 1, 1, 7, tzinfo=CST)))
        self.assertIn("精神", tone_hint(datetime(2026, 1, 1, 12, tzinfo=CST)))
        self.assertIn("放松", tone_hint(datetime(2026, 1, 1, 20, tzinfo=CST)))

    def test_prompt_has_tone(self):
        import botv.ai.client as client
        import botv.memory.context as mem
        from botv.core import locks
        captured = {}

        async def fake_ds(msgs, max_tokens=None, target_id=None):
            captured["sys"] = msgs[0]["content"]
            return "好"

        orig_ds, orig_ev = client.call_deepseek, mem.load_events_from_db
        client.call_deepseek = fake_ds
        mem.load_events_from_db = lambda *a, **k: []
        locks._model_sem = None
        try:
            asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            client.call_deepseek = orig_ds
            mem.load_events_from_db = orig_ev
        self.assertIn("你现在的状态", captured["sys"])
        self.assertNotIn("{tone}", captured["sys"])

class TestTools(unittest.TestCase):
    """v13-U22：工具调用协议"""

    def test_parse_call(self):
        from botv.ai.tools import parse_call
        name, arg, body = parse_call("我查一下\n@tool: recall(答辩)\n稍等")
        self.assertEqual(name, "recall")
        self.assertEqual(arg, "答辩")
        self.assertNotIn("@tool", body)

    def test_parse_no_call(self):
        from botv.ai.tools import parse_call
        name, arg, body = parse_call("今天天气不错")
        self.assertIsNone(name)
        self.assertEqual(body, "今天天气不错")

    def test_parse_unknown(self):
        from botv.ai.tools import parse_call
        name, _arg, _body = parse_call("@tool: fly(天空)")
        self.assertEqual(name, "fly")

    def test_tool_prompt_lists_tools(self):
        from botv.ai.tools import tool_prompt, TOOLS
        text = tool_prompt()
        for name in TOOLS:
            self.assertIn(name, text)

    def test_unknown_tool(self):
        import asyncio
        from botv.ai.tools import run_tool
        out = asyncio.run(run_tool("fly", "天空", "1"))
        self.assertIn("没有这个工具", out)

    def test_empty_args(self):
        import asyncio
        from botv.ai.tools import run_tool
        out = asyncio.run(run_tool("remember", "", "1"))
        self.assertIn("没给内容", out)

    def test_system_prompt_has_tools(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        self.assertIn("@tool:", get_system_prompt())

class TestVision(unittest.TestCase):
    """v11-A8/A6：看图拿描述和标签"""

    def test_parse_fullwidth_colon(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("描述：一只橘猫趴在窗台上打哈欠\n标签：猫,橘猫,窗台,打哈欠")
        self.assertIn("橘猫", desc)
        self.assertEqual(tags[:2], ["猫", "橘猫"])

    def test_parse_ascii_colon(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("描述: 两个人在吃火锅\n标签: 火锅,朋友")
        self.assertIn("火锅", desc)
        self.assertIn("朋友", tags)

    def test_parse_no_format(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("完全没按格式的一段话")
        self.assertEqual(desc, "完全没按格式的一段话")
        self.assertEqual(tags, [])

    def test_tags_capped(self):
        from botv.ai.vision import parse_reply
        _d, tags = parse_reply("标签：a,b,c,d,e,f,g,h")
        self.assertLessEqual(len(tags), 5)

    def test_no_key_returns_empty(self):
        import asyncio
        import botv.ai.vision as V
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = ""
        try:
            desc, tags = asyncio.run(V.describe_image(b"\xff\xd8fake"))
        finally:
            cfg.DS_API_KEY = orig
        self.assertIsNone(desc)
        self.assertEqual(tags, [])

class TestVoice(unittest.TestCase):
    """v11-A10：语音的择时与降级"""

    def setUp(self):
        import botv.chat.send as S
        self.S = S
        self.sent = []
        self._orig = {}
        self._patch("tts_synth", self._fake_synth)
        self._patch("send_voice", self._fake_send)
        S._last_voice_ts.clear()

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(self.S, name, fn)
        self.S._last_voice_ts.clear()

    def _patch(self, name, fn):
        self._orig.setdefault(name, getattr(self.S, name))
        setattr(self.S, name, fn)

    async def _fake_synth(self, text):
        return b"FAKE_MP3"

    async def _fake_send(self, *args, **kwargs):
        self.sent.append(args)

    def _run(self, text="今天天气不错啊", target="1", is_group=False, prob=0.0):
        import asyncio
        orig_random = self.S.random.random
        self.S.random.random = lambda: prob
        try:
            return asyncio.run(self.S.maybe_send_voice(text, target, None, is_group))
        finally:
            self.S.random.random = orig_random

    def test_fires(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.sent), 1)

    def test_group_never(self):
        self.assertFalse(self._run(is_group=True))
        self.assertEqual(self.sent, [])

    def test_too_short(self):
        self.assertFalse(self._run(text="嗯"))
        self.assertEqual(self.sent, [])

    def test_too_long(self):
        self.assertFalse(self._run(text="啊" * 200))
        self.assertEqual(self.sent, [])

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.sent, [])

    def test_cooldown(self):
        self.assertTrue(self._run())
        self.assertFalse(self._run(), "20 分钟内不该再发")

    def test_synth_failure_degrades(self):
        self._patch("tts_synth", lambda text: self._none())
        self.assertFalse(self._run())
        self.assertEqual(self.sent, [])

    async def _none(self):
        return None

if __name__ == "__main__":
    unittest.main()

class TestChatModelAdapters(unittest.TestCase):

    def test_isinstance_protocol(self):
        self.assertIsInstance(model_mod.DeepSeekModel(), ChatModel)
        self.assertIsInstance(model_mod.DoubaoModel(), ChatModel)

    def test_deepseek_wraps_call(self):
        captured = {}

        async def fake(msgs, max_tokens=None, target_id=None):
            captured["n"] = len(msgs)
            return "哼"

        orig = model_mod.call_deepseek
        model_mod.call_deepseek = fake
        try:
            reply = asyncio.run(model_mod.DeepSeekModel().complete(
                ChatRequest(messages=[{"role": "user", "content": "hi"}])))
        finally:
            model_mod.call_deepseek = orig
        self.assertEqual(reply.text, "哼")
        self.assertEqual(reply.model, "deepseek")
        self.assertEqual(captured["n"], 1)

    def test_deepseek_empty_returns_none(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return None

        orig = model_mod.call_deepseek
        model_mod.call_deepseek = fake
        try:
            reply = asyncio.run(model_mod.DeepSeekModel().complete(
                ChatRequest(messages=[{"role": "user", "content": "hi"}])))
        finally:
            model_mod.call_deepseek = orig
        self.assertIsNone(reply)

class TestFallbackChain(unittest.TestCase):

    def _model(self, name, result):
        class M:
            supports_vision = False

            async def complete(self, req):
                return ChatReply(text=result, model=name) if result else None
        M.name = name
        return M()

    def test_first_wins(self):
        chain = FallbackChain([self._model("a", "A"), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "A")

    def test_fallback_on_none(self):
        chain = FallbackChain([self._model("a", None), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "B")

    def test_all_fail(self):
        chain = FallbackChain([self._model("a", None), self._model("b", None)])
        self.assertIsNone(asyncio.run(chain.complete(ChatRequest(messages=[]))))

    def test_exception_falls_through(self):
        class Boom:
            name = "boom"
            supports_vision = False

            async def complete(self, req):
                raise RuntimeError("炸了")

        chain = FallbackChain([Boom(), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "B")

class TestTransport(unittest.TestCase):

    def test_isinstance_protocol(self):
        self.assertIsInstance(QqTransport(FakeWS()), Transport)

    def test_send_private(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.send(Target(kind="private", id=123), [Segment(type="text", data={"text": "hi"})]))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_private_msg")
        self.assertEqual(payload["params"]["user_id"], 123)
        self.assertEqual(payload["params"]["message"][0]["data"]["text"], "hi")

    def test_send_group(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.send(Target(kind="group", id=456), [Segment(type="image", data={"file": "/a.jpg"})]))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_group_msg")
        self.assertEqual(payload["params"]["group_id"], 456)

    def test_poke(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.poke(Target(kind="group", id=456), 789))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_poke")
        self.assertEqual(payload["params"]["user_id"], 789)
        self.assertEqual(payload["params"]["group_id"], 456)



class TestImageKeywordFallback(unittest.TestCase):
    """v17.9：图片关键词只从用户原文补，不从她的回复里抽"""

    def test_uses_user_text(self):
        import botv.ai.client as C

        seen = []
        orig = C.extract_keywords
        C.extract_keywords = lambda text: seen.append(text) or ["下雨", "天气"]
        try:
            kws = C._fallback_img_keywords(
                [{"role": "user", "content": "今天下雨了"}],
                "图没出来。还有，都几点了")
        finally:
            C.extract_keywords = orig

        self.assertEqual(kws, ["下雨", "天气"])
        self.assertIn("下雨", seen[0], "应当拿用户原文去抽词")
        self.assertNotIn("几点", seen[0], "不该拿她的回复抽词")

    def test_empty_user_text_gives_no_keywords(self):
        import botv.ai.client as C

        msgs = [{"role": "user", "content": ""}]
        self.assertEqual(C._fallback_img_keywords(msgs, "随便说点什么"), [],
                         "用户没打字就不该补关键词")

    def test_no_user_message(self):
        import botv.ai.client as C

        self.assertEqual(C._fallback_img_keywords([], "回复"), [])


if __name__ == "__main__":
    unittest.main()
