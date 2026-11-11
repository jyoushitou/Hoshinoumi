# 聊天链路：解析、分条、延迟、群聊闸门、撤回/戳/引用

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

class TestAtDetection(unittest.TestCase):
    """v6-E29：@ 判断"""

    def test_at_me(self):
        from botv.chat.inbound import is_at_me
        msg = [{"type": "text", "data": {"text": "hi"}},
               {"type": "at", "data": {"qq": "12345"}}]
        self.assertTrue(is_at_me(msg, 12345))
        self.assertFalse(is_at_me(msg, 999))
        self.assertFalse(is_at_me("plain text", 12345))

    def test_no_self_qq(self):
        from botv.chat.inbound import is_at_me
        msg = [{"type": "at", "data": {"qq": "12345"}}]
        self.assertFalse(is_at_me(msg, 0))

class TestBubbleDelay(unittest.TestCase):
    """v6-A12：气泡间隔随机，不是固定值"""

    def test_range(self):
        from botv.chat.send import bubble_delay, BUBBLE_DELAY_RANGE
        lo, hi = BUBBLE_DELAY_RANGE
        samples = [bubble_delay() for _ in range(200)]
        self.assertTrue(all(lo <= d <= hi for d in samples))
        self.assertGreater(len(set(samples)), 1, "应该是随机的")

class TestChatImpulse(unittest.TestCase):
    """v10.4：30 分钟一次的主动闲聊掷骰"""

    class _R:
        def __init__(self, v=0.0):
            self.v = v

        def random(self):
            return self.v

    def _now(self, hour, minute=0):
        from datetime import datetime
        from botv.config import CST
        return datetime(2026, 11, 9, hour, minute, tzinfo=CST)

    def test_night_is_zero(self):
        from botv.life.impulse import chat_probability
        self.assertEqual(chat_probability(self._now(3), 5, {"lonely": 1, "mood": 1}), 0.0)

    def test_silence_raises(self):
        from botv.life.impulse import chat_probability
        st = {"lonely": 0.3, "mood": 0.0}
        short = chat_probability(self._now(19), 0.5, st)
        long = chat_probability(self._now(19), 4, st)
        self.assertGreater(long, short)

    def test_life_event_boosts(self):
        from botv.life.impulse import chat_probability
        st = {"lonely": 0.3, "mood": 0.0}
        plain = chat_probability(self._now(19), 3, st, has_life_event=False)
        boosted = chat_probability(self._now(19), 3, st, has_life_event=True)
        self.assertGreater(boosted, plain)
        self.assertAlmostEqual(boosted / plain, 1.8, places=2)

    def test_probability_capped(self):
        from botv.life.impulse import chat_probability, CHAT_MAX_P
        st = {"lonely": 1.0, "mood": 1.0}
        self.assertLessEqual(chat_probability(self._now(19), 99, st, True), CHAT_MAX_P)

    def test_should_chat_blocks(self):
        from botv.life.impulse import should_chat
        ok, why, _p = should_chat(now=self._now(3), state={"lonely": 1}, rng=self._R(0.0))
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

    def test_should_chat_roll(self):
        from botv.life.impulse import should_chat
        st = {"lonely": 0.3, "mood": 0.0}
        miss, _w, _p = should_chat(now=self._now(19), state=st, rng=self._R(0.99),
                                   silent_hours=4, last_user_ts=0.0,
                                   proactive_count=0, unanswered=0, last_proactive_ts=0.0)
        hit, _w2, _p2 = should_chat(now=self._now(19), state=st, rng=self._R(0.0),
                                    silent_hours=4, last_user_ts=0.0,
                                    proactive_count=0, unanswered=0, last_proactive_ts=0.0)
        self.assertFalse(miss)
        self.assertTrue(hit)

class TestFallback(unittest.TestCase):
    """F2：兜底文案不得入库、不得污染关键词"""

    def test_fallback_is_str(self):
        from botv.core.types import Fallback
        f = Fallback("哼")
        self.assertIsInstance(f, str)
        self.assertEqual(f, "哼")

    def test_get_character_reply_marks_fallback(self):
        import botv.ai.client as client
        import botv.memory.context as mem
        from botv.core.types import Fallback

        async def no_ds(*a, **k):
            return None

        async def fb_doubao(*a, **k):
            return Fallback("哼(扭头)")

        orig_ds, orig_db = client.call_deepseek, client.call_doubao
        orig_ev = mem.load_events_from_db
        client.call_deepseek, client.call_doubao = no_ds, fb_doubao
        mem.load_events_from_db = lambda *a, **k: []  # 测试环境不连库
        try:
            r = asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            client.call_deepseek, client.call_doubao = orig_ds, orig_db
            mem.load_events_from_db = orig_ev
        self.assertIsInstance(r, Fallback)

    def test_add_memory_skips_fallback(self):
        import botv.memory.context as mem
        from botv.core.types import Fallback

        calls = []
        orig = mem.add_user_memory_to_db
        orig_kw = mem.add_global_keywords_to_db
        mem.add_user_memory_to_db = lambda *a, **k: calls.append(a)
        mem.add_global_keywords_to_db = lambda *a, **k: None  # 测试环境不连库
        try:
            mem.add_target_memory("1", "hi", Fallback("哼"))
            mem.add_target_memory("1", "hi", "正常回复")
        finally:
            mem.add_user_memory_to_db = orig
            mem.add_global_keywords_to_db = orig_kw
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], "正常回复")

class TestGateBypass(unittest.TestCase):
    """v10-U9b：承诺/锚点不受孤独门槛限制"""

    def test_bypass_lonely(self):
        from datetime import datetime
        from botv.config import CST
        from botv.life.impulse import should_reach_out

        class R:
            def random(self):
                return 0.0
        now = datetime.now(CST).replace(hour=20)
        ok, why = should_reach_out(now=now, state={"lonely": 0.0, "mood": 0.0},
                                   rng=R(), require_lonely=False,
                                   last_user_ts=0.0, proactive_count=0, unanswered=0)
        self.assertTrue(ok, why)

    def test_still_blocked_at_night(self):
        from datetime import datetime
        from botv.config import CST
        from botv.life.impulse import should_reach_out

        class R:
            def random(self):
                return 0.0
        now = datetime.now(CST).replace(hour=2)
        ok, why = should_reach_out(now=now, state={"lonely": 0.9},
                                   rng=R(), require_lonely=False)
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

class TestGroupGate(unittest.TestCase):
    """v6-E29：群聊节奏闸门"""

    def setUp(self):
        cfg.group_last_reply_ts.clear()
        cfg.group_msg_window.clear()

    def tearDown(self):
        cfg.group_last_reply_ts.clear()
        cfg.group_msg_window.clear()

    def test_addressed_passes(self):
        from botv.chat import handler as h
        orig = h.random.random
        h.random.random = lambda: 0.0  # v14-B4：被@ 也要掷骰，测试要压到必中
        try:
            ok, why = h.should_answer_group(111, True)
        finally:
            h.random.random = orig
        self.assertTrue(ok)
        self.assertTrue(why.startswith("被@"), why)

    def test_cooldown_blocks_unaddressed(self):
        from botv.chat.handler import should_answer_group, note_group_reply
        note_group_reply(111)
        ok, why = should_answer_group(111, False)
        self.assertFalse(ok)
        self.assertIn("冷却", why)

    def test_window_full_blocks_even_addressed(self):
        from botv.chat import handler as h
        for _ in range(h.GROUP_WINDOW_MAX):
            h.note_group_reply(222)
        ok, why = h.should_answer_group(222, True)
        self.assertFalse(ok)
        self.assertIn("60秒内", why)

    def test_probability_gate(self):
        from botv.chat import handler as h
        orig = h.random
        try:
            h.random = _FakeRandom(0.0)  # 一定命中
            ok, why = h.should_answer_group(333, False)
            self.assertTrue(ok)
            self.assertTrue(why.startswith("随机接话"), why)

            h.cfg.group_last_reply_ts.clear()
            h.random = _FakeRandom(0.99)  # 一定不中
            ok, why = h.should_answer_group(333, False)
            self.assertFalse(ok)
            self.assertIn("概率", why)
        finally:
            h.random = orig

class TestGroupProbability(unittest.TestCase):
    """v10：群聊回话概率随状态浮动"""

    def test_base(self):
        from botv.chat.handler import group_reply_probability, GROUP_BASE_PROB
        p = group_reply_probability({"lonely": 0.2, "mood": 0.1}, 0)
        self.assertAlmostEqual(p, GROUP_BASE_PROB, places=3)

    def test_lonely_raises(self):
        from botv.chat.handler import group_reply_probability
        quiet = group_reply_probability({"lonely": 0.2, "mood": 0.0}, 0)
        lonely = group_reply_probability({"lonely": 0.9, "mood": 0.0}, 0)
        self.assertGreater(lonely, quiet)

    def test_bad_mood_lowers(self):
        from botv.chat.handler import group_reply_probability
        good = group_reply_probability({"lonely": 0.9, "mood": 0.5}, 0)
        bad = group_reply_probability({"lonely": 0.9, "mood": -0.5}, 0)
        self.assertLess(bad, good)

    def test_unanswered_halves(self):
        from botv.chat.handler import (group_reply_probability,
                                       GROUP_UNANSWERED_LIMIT, GROUP_UNANSWERED_DECAY)
        normal = group_reply_probability({"lonely": 0.9, "mood": 0.0}, 0)
        quiet = group_reply_probability({"lonely": 0.9, "mood": 0.0}, GROUP_UNANSWERED_LIMIT)
        self.assertAlmostEqual(quiet, normal * GROUP_UNANSWERED_DECAY, places=3)

    def test_clamped(self):
        from botv.chat.handler import (group_reply_probability, GROUP_PROB_MIN, GROUP_PROB_MAX)
        for lonely in (0.0, 0.5, 1.0):
            for mood in (-1.0, 0.0, 1.0):
                p = group_reply_probability({"lonely": lonely, "mood": mood}, 0)
                self.assertGreaterEqual(p, GROUP_PROB_MIN)
                self.assertLessEqual(p, GROUP_PROB_MAX)

    def test_streak_increments_and_resets(self):
        from botv.chat import handler as h
        cfg.group_streak.clear()
        h.note_group_reply(555)
        h.note_group_reply(555)
        self.assertEqual(cfg.group_streak[555], 2)
        cfg.group_streak.clear()

class TestMerge(unittest.TestCase):
    """v16：HTML 骨架 + OCR 补字"""

    def test_merge_fills_pua(self):
        from botv.life.ocr import merge_html_ocr
        html = "一座\ue000旧的道观里，黑夜带来了阳光\ue001曾给过的冷寂。"
        ocr = "一座破旧的道观里，黑夜带来了阳光未曾给过的冷寂。"
        self.assertEqual(merge_html_ocr(html, ocr),
                         "一座破旧的道观里，黑夜带来了阳光未曾给过的冷寂。")

    def test_merge_keeps_html_when_clean(self):
        from botv.life.ocr import merge_html_ocr
        html = "他推开门。外面在下雨。"
        ocr = "他推开门。外面在下兩。"   # OCR 错字
        self.assertIn("下雨", merge_html_ocr(html, ocr), "已知字用 HTML，别被 OCR 带错")

    def test_merge_without_inputs(self):
        from botv.life.ocr import merge_html_ocr
        self.assertEqual(merge_html_ocr("", "abc"), "abc")
        self.assertEqual(merge_html_ocr("abc", ""), "abc")
        self.assertEqual(merge_html_ocr("", ""), "")

    def test_merge_drops_leftover_pua(self):
        from botv.life.ocr import merge_html_ocr, pua_ratio
        html = "开头\ue000\ue001结尾"
        ocr = "开头结尾"          # OCR 也没认出来
        merged = merge_html_ocr(html, ocr)
        self.assertEqual(pua_ratio(merged), 0.0)

    def test_best_text_prefers_merged(self):
        from botv.life.ocr import best_text
        html = "一座\ue000旧的道观" + "很长的正文内容" * 20
        ocr = "一座破旧的道观" + "很长的正文内容" * 20
        self.assertIn("破旧", best_text(html, ocr))

    def test_fetch_chapter_merges(self):
        import asyncio
        import botv.life.ocr as O
        import botv.life.novel as N

        async def fake_html(url):
            return '<div class="muye-reader-content">一座\ue000旧的道观' + ("正文" * 200) + "</div>"

        async def fake_ocr(url):
            return "一座破旧的道观" + ("正文" * 200)

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/3"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("破旧", text)
        self.assertNotIn("\ue000", text)

class TestParse(unittest.TestCase):
    """AI 回复解析"""

    def test_five_lines(self):
        ans = "你好\n（歪头）\n关键词搜索图片用：猫,狗\n事件摘要：测试 | 标签：a,b\n关键词提炼：a,b"
        dialog, action, img_kw, event, refined = parse_ai_reply(ans)
        self.assertEqual(dialog, "你好")
        self.assertEqual(action, "（歪头）")
        self.assertEqual(img_kw, ["猫", "狗"])
        self.assertEqual(event, "测试")
        self.assertEqual(refined, ["a", "b"])

    def test_single_line(self):
        dialog, action, img_kw, event, refined = parse_ai_reply("只有一句话")
        self.assertEqual(dialog, "只有一句话")
        self.assertEqual(action, "")
        self.assertEqual(img_kw, [])

    def test_none_action(self):
        _, action, _, _, _ = parse_ai_reply("嗯\n（无）")
        self.assertEqual(action, "")

    def test_empty_input(self):
        self.assertEqual(parse_ai_reply(None), ("嗯嗯", "", [], "", []))

class TestPoke(unittest.TestCase):
    """v12-A16：戳一戳回戳"""

    def test_detect(self):
        from botv.chat.notice import is_poke
        self.assertTrue(is_poke({"post_type": "notice", "notice_type": "notify", "sub_type": "poke"}))
        self.assertFalse(is_poke({"post_type": "message"}))
        self.assertFalse(is_poke({"post_type": "notice", "notice_type": "notify", "sub_type": "other"}))

    def test_reply_back_in_group(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append((action, params))

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "1001", "user_id": "2002", "group_id": 123}
        ok = asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertTrue(ok)
        self.assertEqual(calls[0][0], "group_poke")
        self.assertEqual(calls[0][1]["user_id"], "2002")

    def test_reply_back_private(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append((action, params))

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "1001", "user_id": "2002"}
        asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertEqual(calls[0][0], "friend_poke")

    def test_ignore_poke_others(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append(action)

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "9999", "user_id": "2002"}
        ok = asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertFalse(ok)
        self.assertEqual(calls, [])

class TestQuotedReply(unittest.TestCase):
    """v12-A15：引用回复标记"""

    def test_marker_without_ws(self):
        import asyncio
        from botv.chat.inbound import parse_message_content
        raw = [{"type": "reply", "data": {"id": 123}},
               {"type": "text", "data": {"text": "这个咋样"}}]
        text, _md5 = asyncio.run(parse_message_content(raw, "1", None))
        self.assertIn("引用", text)
        self.assertIn("这个咋样", text)

class TestReplyAssembly(unittest.TestCase):
    """回复组装：当前行为快照"""

    def setUp(self):
        cfg.CODE_MODE = False
        # 图片搜索依赖数据库，测试里直接短路
        self._orig_get_best_image = reply_mod.get_best_image

        async def _no_image(*args, **kwargs):
            return None

        reply_mod.get_best_image = _no_image

    def tearDown(self):
        reply_mod.get_best_image = self._orig_get_best_image

    def _build(self, text):
        parts = asyncio.run(reply_mod.build_reply_message(text, "10001"))
        return [seg[0]["data"]["text"] for kind, seg in parts if kind == "text"]

    def test_first_two_lines_sent(self):
        texts = self._build("第一句\n（笑）")
        self.assertEqual(texts, ["第一句", "（笑）"])

    def test_multiline_dialog_one_bubble_per_line(self):
        """v6-A12：一行一个气泡，行数由模型决定"""
        texts = self._build("第一句\n第二句\n第三句")
        self.assertEqual(texts, ["第一句", "第二句", "第三句"])

    def test_too_many_lines_merged(self):
        """异常保护：只有超过 10 行才合并尾部"""
        text = "\n".join(f"第{i}行" for i in range(1, 16))
        texts = self._build(text)
        self.assertEqual(len(texts), 10)
        self.assertIn("第15行", texts[-1])

    def test_no_action_sends_no_bubble(self):
        """F1：无动作时不该补一条「（无）」"""
        texts = self._build("只有对话")
        self.assertEqual(texts, ["只有对话"])

    def test_meta_lines_not_sent(self):
        """元数据按标记识别，不进对话"""
        texts = self._build("正文\n关键词搜索图片用：猫\n事件摘要：x\n关键词提炼：a")
        self.assertEqual(texts, ["正文"])

    def test_code_mode_single_message(self):
        """F3：代码模式整段发一条，代码块不被拆散"""
        cfg.CODE_MODE = True
        texts = self._build("答案开头\n```python\nprint(1)\n```\n答案结尾")
        self.assertEqual(len(texts), 1)
        self.assertIn("print(1)", texts[0])
        self.assertIn("答案结尾", texts[0])

class TestReplyTiming(unittest.TestCase):
    """v6-A1：延迟按时段浮动，且偏短"""

    class _R:
        def __init__(self, v):
            self.v = v

        def random(self):
            return self.v

    def test_bands(self):
        from datetime import datetime
        from botv.chat.timing import delay_range
        from botv.config import CST
        self.assertEqual(delay_range(datetime(2026, 1, 1, 2, tzinfo=CST)), (20, 180))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 10, tzinfo=CST)), (5, 30))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 20, tzinfo=CST)), (8, 60))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 23, 30, tzinfo=CST)), (20, 120))

    def test_within_range(self):
        from datetime import datetime
        from botv.chat.timing import reply_delay
        from botv.config import CST
        now = datetime(2026, 1, 1, 10, tzinfo=CST)
        for v in (0.0, 0.5, 0.999):
            d = reply_delay(now, self._R(v))
            self.assertGreaterEqual(d, 5)
            self.assertLessEqual(d, 30)

    def test_biased_short(self):
        from datetime import datetime
        from botv.chat.timing import reply_delay
        from botv.config import CST
        now = datetime(2026, 1, 1, 10, tzinfo=CST)
        vals = [reply_delay(now, self._R(i / 100)) for i in range(100)]
        mean = sum(vals) / len(vals)
        self.assertLess(mean, 17.5, f"应偏短，实际均值 {mean:.1f}")

class TestShare(unittest.TestCase):
    """v12-A18：分享欲（偶尔补一句自己的事）"""

    def setUp(self):
        import botv.chat.handler as h
        self.h = h
        self.sent = []
        self._orig = {}
        self._patch("get_character_reply", self._fake_reply)
        self._patch("send_short_reply", self._fake_send)
        h._last_share_ts.clear()

        import botv.infra.repo_memory as rm
        self._orig["load_today_life"] = rm.load_today_life
        rm.load_today_life = lambda: ["小咪把多肉推下去了"]

    def tearDown(self):
        import botv.infra.repo_memory as rm
        for name, fn in self._orig.items():
            setattr(self.h, name, fn) if hasattr(self.h, name) else None
        if "load_today_life" in self._orig:
            rm.load_today_life = self._orig["load_today_life"]
        self.h._last_share_ts.clear()

    def _patch(self, name, fn):
        self._orig.setdefault(name, getattr(self.h, name))
        setattr(self.h, name, fn)

    async def _fake_reply(self, prompt, tid):
        return "对了，" + prompt[-20:]

    async def _fake_send(self, *args, **kwargs):
        self.sent.append(args)

    def _run(self, prob=0.0):
        import asyncio
        orig = self.h.random.random
        self.h.random.random = lambda: prob
        try:
            return asyncio.run(self.h.maybe_share_something("1", None))
        finally:
            self.h.random.random = orig

    def test_fires(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.sent), 1)

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.sent, [])

    def test_cooldown(self):
        self.assertTrue(self._run())
        self.assertFalse(self._run(), "40 分钟内不该再分享")

    def test_no_life_event(self):
        import botv.infra.repo_memory as rm
        rm.load_today_life = lambda: []
        self.assertFalse(self._run())

class TestTypoRecall(unittest.TestCase):
    """v12-A13：打错字 → 撤回 → 重发"""

    def setUp(self):
        import botv.chat.send as S
        self.S = S
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.typo_history.clear()
        self.deleted = []
        self._orig = {}
        self._patch("send_private_msg", self._fake_send)
        self._patch("_send_or_queue", self._fake_action)

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(self.S, name, fn)
        self.cfg.typo_history.clear()

    def _patch(self, name, fn):
        self._orig.setdefault(name, getattr(self.S, name))
        setattr(self.S, name, fn)

    async def _fake_send(self, target, msg, ws, want_response=False):
        return {"status": "ok", "data": {"message_id": 4242}}

    async def _fake_action(self, action, params, ws, label, **kw):
        self.deleted.append((action, params))
        return True

    def test_make_typo_differs(self):
        from botv.chat.send import make_typo
        text = "明天下午三点面试"
        typo = make_typo(text)
        self.assertNotEqual(typo, text)
        self.assertEqual(len(typo), len(text))

    def test_short_text_no_typo(self):
        from botv.chat.send import make_typo
        self.assertEqual(make_typo("在吗"), "在吗")

    def _run(self, text="明天下午三点面试", prob=0.0):
        import asyncio
        orig = self.S.random.random
        self.S.random.random = lambda: prob
        try:
            return asyncio.run(self.S.try_typo_recall("1", text, None))
        finally:
            self.S.random.random = orig

    def test_full_flow(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.deleted), 1)
        self.assertEqual(self.deleted[0][0], "delete_msg")
        self.assertEqual(self.deleted[0][1]["message_id"], 4242)
        self.assertEqual(len(self.cfg.typo_history), 1)

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.deleted, [])

    def test_weekly_quota(self):
        import time
        self.cfg.typo_history.extend([time.time(), time.time()])
        self.assertFalse(self._run(), "一周最多两次")
        self.assertEqual(self.deleted, [])

    def test_no_message_id_degrades(self):
        async def bad_send(target, msg, ws, want_response=False):
            return {"status": "failed"}
        self._patch("send_private_msg", bad_send)
        self.assertFalse(self._run())
        self.assertEqual(self.deleted, [])

if __name__ == "__main__":
    unittest.main()



class TestImageFallbackWording(unittest.TestCase):
    """v17.9：图收到了、视觉失败 → 不能说「没加载出来」"""

    def _run_parse(self, desc, tags, download_ok=True):
        import asyncio
        import botv.chat.inbound as I

        orig = (I.download_url, I.process_and_save_image, I.describe_image)
        # download_url 跑在 run_blocking 的线程里，必须是同步函数
        I.download_url = lambda url: b"JPEGDATA" if download_ok else None

        async def fake_proc(data, url, uid, keywords=None):
            return "md5x", "标签", "/tmp/x.jpg"

        I.process_and_save_image = fake_proc
        async def fake_vision(data):
            return desc, tags

        I.describe_image = fake_vision
        try:
            msg = [{"type": "image", "data": {"url": "http://x/a.jpg"}}]
            text, md5s = asyncio.run(I.parse_message_content(msg, "1", None))
        finally:
            (I.download_url, I.process_and_save_image, I.describe_image) = orig
        return text

    def test_vision_empty_not_missing(self):
        text = self._run_parse(None, [])
        self.assertNotIn("没加载出来", text)
        self.assertNotIn("没加载", text)

    def test_vision_ok_uses_desc(self):
        text = self._run_parse("一只猫在窗台", ["猫"])
        self.assertIn("一只猫", text)


async def _async(v):
    return v




class TestPureEmoji(unittest.TestCase):
    """v17.9：用户发表情 → 正常对话，不是「她要发表情包」"""

    def test_placeholder_not_sticker_request(self):
        from botv.chat.inbound import contains_sticker_key

        self.assertFalse(contains_sticker_key("[表情5]"),
                         "[表情5] 是占位符，不该当请求")
        self.assertFalse(contains_sticker_key("[图][表情3]"))

    def test_real_request_still_works(self):
        from botv.chat.inbound import contains_sticker_key

        self.assertTrue(contains_sticker_key("发个表情包"))
        self.assertTrue(contains_sticker_key("来个表情"))

    def test_pure_emoji_becomes_sentence(self):
        import asyncio
        import botv.chat.inbound as I

        orig = I.download_url
        I.download_url = lambda url: b"x"
        try:
            msg = [{"type": "face", "data": {"id": "5"}}]
            text, _ = asyncio.run(I.parse_message_content(msg, "1", None))
        finally:
            I.download_url = orig
        self.assertIn("表情", text)
        self.assertNotIn("[表情", text, "不该把占位符原样喂给模型")




class TestVoiceSkipsTypoRecall(unittest.TestCase):
    """v17.9：语音念过了就别再撤文字（说写不一致）"""

    def setUp(self):
        import botv.chat.send as S

        self.S = S
        self.S._last_voice_ts.clear()
        self._orig = (S.send_private_msg, S._send_or_queue)

    def tearDown(self):
        self.S._last_voice_ts.clear()
        self.S.send_private_msg, self.S._send_or_queue = self._orig

    def test_skip_after_voice(self):
        import asyncio
        import time

        self.S._last_voice_ts["1"] = time.time()      # 刚刚发过语音
        called = []

        async def fake_send(*a, **k):
            called.append(a)
            return {"data": {"message_id": 1}}

        self.S.send_private_msg = fake_send
        ok = asyncio.run(self.S.try_typo_recall("1", "没有就是没吃", None))
        self.assertFalse(ok, "发过语音就不该再演撤回")
        self.assertEqual(called, [], "不该发出错字版本")

    def test_normal_path_unaffected(self):
        """没有语音时逻辑不变（概率 0 直接 False）"""
        import asyncio

        orig = self.S.TYPO_PROB
        self.S.TYPO_PROB = 0.0
        try:
            ok = asyncio.run(self.S.try_typo_recall("1", "没有就是没吃", None))
        finally:
            self.S.TYPO_PROB = orig
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
