# 记忆与检索：预算、BM25、时间线、画像、浓缩

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

class TestBudget(unittest.TestCase):
    """v8-B13：分层预算"""

    def test_trim(self):
        from bot.memory.inject import trim
        self.assertEqual(trim("abc", 10), "abc")
        self.assertEqual(len(trim("x" * 100, 10)), 10)
        self.assertTrue(trim("x" * 100, 10).endswith("…"))

    def test_cap_lines_keeps_recent(self):
        from bot.memory.inject import cap_lines
        lines = [f"第{i}轮" for i in range(1, 21)]
        text, used = cap_lines(lines, 30)
        self.assertLessEqual(used, 30)
        self.assertIn("第20轮", text)
        self.assertNotIn("第1轮", text)

    def test_cap_lines_all_fit(self):
        from bot.memory.inject import cap_lines
        text, used = cap_lines(["a", "b"], 100)
        self.assertEqual(text, "a\nb")

    def test_report_flag(self):
        from bot.memory.inject import report
        self.assertIn("✅", report(a="x" * 10))

    def test_context_trims_dialogue(self):
        from collections import deque
        import bot.memory.context as ctx
        from bot.memory.inject import BUDGET
        cfg.user_memory_pool["9"] = deque([("长" * 200, "回" * 200)] * 10, maxlen=15)
        orig_l, orig_e = ctx.load_memories_for_search, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            _kw, dia, _ev = ctx.build_memory_context("9", None, query="hi")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e
            cfg.user_memory_pool.pop("9", None)
        self.assertEqual(dia.count("用户:"), 1, "10 轮长对话应被预算砍到 1 轮")

class TestDigest(unittest.TestCase):
    """v14.1-D3：会话浓缩成她自己的记录"""

    def setUp(self):
        import os
        import bot.life.digest as D
        self.D = D
        self.orig_dir = D.DIGEST_DIR
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tmp = os.path.join(root, ".test-digest")
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)   # 先清，避免上次残留污染
        os.makedirs(self.tmp, exist_ok=True)
        D.DIGEST_DIR = self.tmp

    def tearDown(self):
        import shutil
        self.D.DIGEST_DIR = self.orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_append_and_load(self):
        self.assertTrue(self.D.append("u1", "聊了加班的烦心事"))
        text = self.D.load("u1")
        self.assertIn("加班的烦心事", text)

    def test_line_truncated(self):
        self.D.append("u1", "啊" * 200)
        line = self.D.load("u1").splitlines()[-1]
        self.assertLessEqual(len(line), 6 + self.D.MAX_LINE_CHARS)

    def test_max_lines(self):
        for i in range(30):
            self.D.append("u1", f"第{i}件事")
        lines = self.D.load("u1").splitlines()
        self.assertEqual(len(lines), self.D.MAX_LINES)
        self.assertIn("第29件事", lines[-1])
        self.assertNotIn("第0件事", "\n".join(lines))

    def test_compact_fallback(self):
        rounds = [["今天加班到十点", "累就早点睡"], ["猫又把杯子打碎了", "它故意的吧"]]
        line = self.D.compact_from_rounds(rounds)
        self.assertTrue(line)

    def test_update_without_ai_uses_fallback(self):
        import asyncio
        rounds = [["今天加班", "累就别撑"] for _ in range(10)]
        ok = asyncio.run(self.D.update("u2", rounds, summarize=None))
        self.assertTrue(ok)
        self.assertTrue(self.D.load("u2"))

    def test_update_needs_ten_rounds(self):
        import asyncio
        ok = asyncio.run(self.D.update("u3", [["a", "b"]] * 3, summarize=None))
        self.assertFalse(ok)

    def test_empty_descibe(self):
        self.assertEqual(self.D.describe("nobody"), "")

class TestDigestOverflow(unittest.TestCase):
    """v14.1-D3：超过 30 轮才浓缩"""

    def setUp(self):
        import os
        from collections import deque
        import bot.life.digest as D
        from bot.core import state as cfg
        self.D, self.cfg = D, cfg
        self.orig_dir = D.DIGEST_DIR
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tmp = os.path.join(root, ".test-digest2")
        os.makedirs(self.tmp, exist_ok=True)
        D.DIGEST_DIR = self.tmp
        cfg.digest_pending.clear()
        cfg.user_memory_pool.clear()

    def tearDown(self):
        import shutil
        self.D.DIGEST_DIR = self.orig_dir
        self.cfg.digest_pending.clear()
        self.cfg.user_memory_pool.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overflow_moves_oldest_to_buffer(self):
        from collections import deque
        import bot.memory.context as ctx
        self.cfg.user_memory_pool["t1"] = deque([["u", "b"]] * 30, maxlen=30)
        orig_u, orig_e = ctx.add_user_memory_to_db, ctx.add_event_to_db
        orig_k = ctx.add_global_keywords_to_db
        ctx.add_user_memory_to_db = lambda *a, **k: None
        ctx.add_event_to_db = lambda *a, **k: None
        ctx.add_global_keywords_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("t1", "新消息", "新回复")
        finally:
            ctx.add_user_memory_to_db, ctx.add_event_to_db = orig_u, orig_e
            ctx.add_global_keywords_to_db = orig_k
        self.assertEqual(len(self.cfg.digest_pending["t1"]), 1, "溢出的一轮要进缓冲")
        self.assertEqual(len(self.cfg.user_memory_pool["t1"]), 30)

    def test_no_buffer_before_30(self):
        from collections import deque
        import bot.memory.context as ctx
        self.cfg.user_memory_pool["t2"] = deque([["u", "b"]] * 5, maxlen=30)
        orig_u, orig_e = ctx.add_user_memory_to_db, ctx.add_event_to_db
        orig_k = ctx.add_global_keywords_to_db
        ctx.add_user_memory_to_db = lambda *a, **k: None
        ctx.add_event_to_db = lambda *a, **k: None
        ctx.add_global_keywords_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("t2", "新消息", "新回复")
        finally:
            ctx.add_user_memory_to_db, ctx.add_event_to_db = orig_u, orig_e
            ctx.add_global_keywords_to_db = orig_k
        self.assertNotIn("t2", self.cfg.digest_pending)

    def test_condense_when_buffer_full(self):
        import asyncio
        self.cfg.digest_pending["t3"] = [["今天加班", "累就别撑"]] * 10
        ok = asyncio.run(self.D.maybe_condense("t3", summarize=None))
        self.assertTrue(ok)
        self.assertEqual(self.cfg.digest_pending["t3"], [])
        self.assertTrue(self.D.load("t3"))

    def test_not_enough_buffer(self):
        import asyncio
        self.cfg.digest_pending["t4"] = [["a", "b"]] * 5
        self.assertFalse(asyncio.run(self.D.maybe_condense("t4", summarize=None)))

class TestImageTagsBackfill(unittest.TestCase):
    """v8-CLIPCUT：用 AI 关键词回写图片标签"""

    def test_merge_and_dedup(self):
        import bot.image.store as store
        cur = _FakeCursor({"tags": "用户发图,猫"})
        orig = store.get_cursor
        store.get_cursor = lambda: cur
        try:
            n = store.update_image_tags(["abc"], ["猫", "可爱"])
        finally:
            store.get_cursor = orig
        self.assertEqual(n, 1)
        upd = [s for s in cur.statements if s[0].startswith("UPDATE")]
        self.assertEqual(upd[0][1][0], "用户发图,猫,可爱")

    def test_empty_keywords_noop(self):
        import bot.image.store as store
        self.assertEqual(store.update_image_tags(["abc"], []), 0)

class TestKeywordScoping(unittest.TestCase):
    """v8-B12：关键词按对象隔离"""

    def setUp(self):
        cfg.global_keyword_set = set()
        cfg.target_keyword_sets = {}

    def tearDown(self):
        cfg.global_keyword_set = set()
        cfg.target_keyword_sets = {}
        cfg.user_memory_pool.pop("A", None)

    def test_context_uses_own_words(self):
        import bot.memory.context as ctx
        cfg.global_keyword_set = {"公共词"}
        cfg.target_keyword_sets = {"A": {"甲的词"}, "B": {"乙的词"}}
        orig_l, orig_e = ctx.load_memories_for_search, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            kw_a, _d, _e = ctx.build_memory_context("A", None, query="x")
            kw_b, _d, _e = ctx.build_memory_context("B", None, query="x")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e
        self.assertIn("甲的词", kw_a)
        self.assertNotIn("乙的词", kw_a)
        self.assertIn("公共词", kw_a)
        self.assertIn("乙的词", kw_b)

    def test_write_goes_to_target(self):
        import bot.memory.context as ctx
        calls = []
        orig_kw, orig_u = ctx.add_global_keywords_to_db, ctx.add_user_memory_to_db
        ctx.add_global_keywords_to_db = lambda kws, tid="": calls.append((tid, list(kws)))
        ctx.add_user_memory_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("A", "hi", "回复", refined_keywords=["词1"])
        finally:
            ctx.add_global_keywords_to_db, ctx.add_user_memory_to_db = orig_kw, orig_u
        self.assertEqual(calls[0][0], "A")
        self.assertEqual(calls[0][1], ["词1"])

class TestLoadMemories(unittest.TestCase):
    """v8-B12：启动时把关键词按对象拆开加载"""

    def test_splits_public_and_personal(self):
        from collections import deque
        import bot.memory.context as ctx
        orig_u, orig_k = ctx.load_user_memories_from_db, ctx.load_keywords_from_db
        ctx.load_user_memories_from_db = lambda: {"A": deque([["hi", "yo"]], maxlen=5)}
        ctx.load_keywords_from_db = lambda: {"": {"公共"}, "A": {"甲"}}
        try:
            ctx.load_memories()
            got_public = set(cfg.global_keyword_set)
            got_target = dict(cfg.target_keyword_sets)
        finally:
            ctx.load_user_memories_from_db, ctx.load_keywords_from_db = orig_u, orig_k
            cfg.global_keyword_set = set()
            cfg.target_keyword_sets = {}
        self.assertEqual(got_public, {"公共"})
        self.assertEqual(got_target.get("A"), {"甲"})

class TestProfile(unittest.TestCase):
    """v7-B9：画像解析与写入"""

    def test_get_profile_parses(self):
        import bot.infra.repo_profile as rp
        cur = _FakeCursor()
        cur.fetchall = lambda: [{"event_summary": "昵称：小奈"},
                                {"event_summary": "喜好：甜"},
                                {"event_summary": "没有冒号的坏数据"}]
        orig = rp.get_cursor
        rp.get_cursor = lambda: cur
        try:
            p = rp.get_profile("1")
        finally:
            rp.get_cursor = orig
        self.assertEqual(p, {"昵称": "小奈", "喜好": "甜"})

    def test_build_text(self):
        import bot.infra.repo_profile as rp
        orig = rp.get_profile
        rp.get_profile = lambda tid: {"昵称": "小奈", "禁忌": "别熬夜"}
        try:
            s = rp.build_profile_text("1")
        finally:
            rp.get_profile = orig
        self.assertIn("昵称=小奈", s)
        self.assertIn("禁忌=别熬夜", s)

    def test_empty_profile(self):
        import bot.infra.repo_profile as rp
        orig = rp.get_profile
        rp.get_profile = lambda tid: {}
        try:
            self.assertEqual(rp.build_profile_text("1"), "无")
        finally:
            rp.get_profile = orig

    def test_set_profile_is_delete_then_insert(self):
        import bot.infra.repo_profile as rp
        cur = _FakeCursor()
        orig = rp.get_cursor
        rp.get_cursor = lambda: cur
        try:
            ok = rp.set_profile("1", "昵称", "小奈")
        finally:
            rp.get_cursor = orig
        self.assertTrue(ok)
        self.assertEqual(cur.verbs()[:2], ["DELETE", "INSERT"])

    def test_set_profile_rejects_empty(self):
        import bot.infra.repo_profile as rp
        self.assertFalse(rp.set_profile("1", "", "x"))
        self.assertFalse(rp.set_profile("1", "昵称", "   "))

class TestRecallMemories(unittest.TestCase):
    """v8-B11：检索接入上下文，命中优先、未命中兜底"""

    def test_uses_retrieval_when_hit(self):
        import bot.memory.context as ctx
        cands = [{"summary": "主人要答辩"}, {"summary": "加班"}]
        orig_l, orig_r = ctx.load_memories_for_search, ctx.retrieve
        ctx.load_memories_for_search = lambda tid, limit=300: cands
        ctx.retrieve = lambda q, ms, top_k=5: [(ms[0], 0.9)]
        try:
            s = ctx._recall_memories("1", "答辩")
        finally:
            ctx.load_memories_for_search, ctx.retrieve = orig_l, orig_r
        self.assertIn("答辩", s)
        self.assertNotIn("加班", s)

    def test_falls_back_when_no_hit(self):
        import bot.memory.context as ctx
        orig_l, orig_r, orig_e = ctx.load_memories_for_search, ctx.retrieve, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: [{"summary": "x"}]
        ctx.retrieve = lambda q, ms, top_k=5: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: [("最近的旧事", "")]
        try:
            s = ctx._recall_memories("1", "无关的查询")
        finally:
            ctx.load_memories_for_search, ctx.retrieve, ctx.load_events_from_db = orig_l, orig_r, orig_e
        self.assertIn("最近的旧事", s)

    def test_db_error_returns_placeholder(self):
        import bot.memory.context as ctx
        orig_l = ctx.load_memories_for_search
        def boom(tid, limit=300):
            raise RuntimeError("db down")
        ctx.load_memories_for_search = boom
        orig_e = ctx.load_events_from_db
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            self.assertEqual(ctx._recall_memories("1", "任何"), "无")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e

class TestRetrieval(unittest.TestCase):
    """v8-B11/B17：BM25 + 关键词 + RRF"""

    MEMS = [
        {"summary": "defense tomorrow at school", "tags": "school", "importance": 4, "hit_count": 0},
        {"summary": "overtime until ten tonight", "tags": "work", "importance": 3, "hit_count": 2},
        {"summary": "cat broke a cup", "tags": "life", "importance": 2, "hit_count": 0},
    ]

    @staticmethod
    def tok(s):
        return [w for w in str(s).lower().split() if len(w) > 1]

    def test_hit_first(self):
        from bot.memory.retrieval import retrieve
        r = retrieve("defense", self.MEMS, top_k=2, tokenizer=self.tok)
        self.assertTrue(r)
        self.assertIn("defense", r[0][0]["summary"])

    def test_no_match_returns_empty(self):
        from bot.memory.retrieval import retrieve
        self.assertEqual(retrieve("quantum", self.MEMS, top_k=2, tokenizer=self.tok), [])

    def test_bm25_orders_correctly(self):
        from bot.memory.retrieval import BM25
        bm = BM25([m["summary"] for m in self.MEMS], tokenizer=self.tok)
        self.assertGreater(bm.score(["overtime"], 1), bm.score(["overtime"], 0))

    def test_rrf_prefers_common_head(self):
        from bot.memory.retrieval import rrf
        fused = rrf([[0, 1, 2], [2, 0, 1]])
        self.assertEqual(fused[0][0], 0)

class TestTimeline(unittest.TestCase):
    """v8-B16：时间线格式"""

    def test_format(self):
        from datetime import date
        from bot.memory.timeline import format_timeline
        rows = [{"day": date(2026, 11, 7), "summary": "答辩"},
                {"day": date(2026, 11, 6), "summary": "加班"}]
        self.assertEqual(format_timeline(rows), "11-07 答辩\n11-06 加班")

    def test_empty(self):
        from bot.memory.timeline import format_timeline
        self.assertEqual(format_timeline([]), "无")

    def test_skip_empty_summary(self):
        from bot.memory.timeline import format_timeline
        rows = [{"day": None, "summary": ""}, {"day": "2026-11-05", "summary": "开会"}]
        s = format_timeline(rows)
        self.assertIn("11-05 开会", s)
        self.assertNotIn("??-??", s)

    def test_trimmed_to_budget(self):
        from bot.memory.timeline import format_timeline
        rows = [{"day": "2026-11-05", "summary": "很长的记忆" * 50}]
        self.assertLessEqual(len(format_timeline(rows)), 200)

if __name__ == "__main__":
    unittest.main()



class TestWeightBoost(unittest.TestCase):
    """v18.2 U3：同等相关时，weight 高的排前面"""

    def test_heavy_wins_tie(self):
        from bot.memory.retrieval import retrieve

        mems = [
            {"summary": "今天吃了面", "tags": "吃饭", "importance": 3,
             "hit_count": 0, "weight": 0.3},
            {"summary": "我妈住院了", "tags": "家里 医院", "importance": 3,
             "hit_count": 0, "weight": 0.9},
        ]
        out = retrieve("住院 家里", mems, top_k=2, tokenizer=lambda q: ["住院", "家里"])
        self.assertTrue(out, "应该有结果")
        self.assertEqual(out[0][0]["summary"], "我妈住院了", "重的应排前")

    def test_no_weight_falls_back_default(self):
        from bot.memory.retrieval import retrieve

        mems = [{"summary": "测试一条", "tags": "测试", "importance": 3, "hit_count": 0}]
        out = retrieve("测试", mems, top_k=1, tokenizer=lambda q: ["测试"])
        self.assertEqual(len(out), 1, "缺 weight 不该报错")

    def test_zero_weight_still_returned(self):
        from bot.memory.retrieval import retrieve

        mems = [{"summary": "很轻松的事", "tags": "轻松", "importance": 1,
                 "hit_count": 0, "weight": 0.0}]
        out = retrieve("轻松", mems, top_k=1, tokenizer=lambda q: ["轻松"])
        self.assertTrue(out, "weight=0 也要能检索到（只是排后）")


if __name__ == "__main__":
    unittest.main()
