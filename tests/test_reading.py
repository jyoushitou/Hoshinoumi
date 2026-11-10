# 读小说：抓取解析、OCR、进度、分享

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

class TestBareTitleRequest(unittest.TestCase):
    """v16.0.4：没有书名号也能认出来 + 按书名搜索"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.life.reading as R
        self.R = R
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def test_detect_bare_title(self):
        got = self.R.detect_book_request("去看看十日终焉呢？")
        self.assertEqual(got["title"], "十日终焉", "别把「呢」吃进书名")

    def test_detect_bare_title_other_particle(self):
        got = self.R.detect_book_request("看看十日终焉吧")
        self.assertEqual(got["title"], "十日终焉")

    def test_plain_chat_not_detected(self):
        self.assertIsNone(self.R.detect_book_request("你上课了吗"))
        self.assertIsNone(self.R.detect_book_request("今天天气不错"))

    def test_follow_with_search(self):
        import asyncio

        async def search(title):
            return ("十日终焉", "https://fanqienovel.com/page/999")

        async def fetch_book(url):
            return {"title": "十日终焉", "intro": "无限流", "chapters": []}

        book, msg = asyncio.run(self.R.follow(
            "30", title="十日终焉", search=search, fetch_book=fetch_book))
        self.assertIsNotNone(book)
        self.assertEqual(book["url"], "https://fanqienovel.com/page/999")
        self.assertIn("好，我去看", msg)

    def test_follow_search_miss_asks_link(self):
        import asyncio

        async def search(title):
            return None

        book, msg = asyncio.run(self.R.follow("31", title="找不到的书", search=search))
        self.assertIsNone(book)
        self.assertIn("链接", msg)

    def test_follow_without_search(self):
        import asyncio
        book, msg = asyncio.run(self.R.follow("32", title="十日终焉"))
        self.assertIsNone(book)
        self.assertIn("链接", msg)

class TestCookies(unittest.TestCase):
    """v16：登录态注入（多路径 + 多格式）"""

    def setUp(self):
        import os
        import botv.life.cookies as C
        self.C = C
        self.orig = C.FALLBACKS
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dir = os.path.join(root, ".test-cookies")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        import shutil
        self.C.FALLBACKS = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, data):
        import json, os
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.C.FALLBACKS = (path,)
        return path

    ARR = [
        {"name": "_csrfToken", "value": "abc1234", "domain": ".qidian.com", "path": "/"},
        {"name": "ywopenid", "value": "xyz9999", "domain": ".qidian.com"},
    ]

    def test_array_format(self):
        self._write("cookies.json", self.ARR)
        items = self.C.for_site("qidian")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["domain"], ".qidian.com")

    def test_grouped_format(self):
        self._write("root.json", {"qidian": self.ARR})
        self.assertEqual(len(self.C.for_site("qidian")), 2)

    def test_domain_autofill(self):
        self._write("c.json", [{"name": "a", "value": "b"}])
        items = self.C.for_site("qidian")
        self.assertEqual(items[0]["domain"], ".qidian.com", "没给域名就按站点补")

    def test_missing_returns_empty(self):
        import os
        self.C.FALLBACKS = (os.path.join(self.dir, "nope.json"),)
        self.assertEqual(self.C.for_site("qidian"), [])
        self.assertEqual(self.C.describe(), [])

    def test_bad_json_ignored(self):
        import os
        path = os.path.join(self.dir, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{不是 json")
        self.C.FALLBACKS = (path,)
        self.assertEqual(self.C.for_site("qidian"), [])

    def test_no_value_leak_in_describe(self):
        self._write("c.json", {"qidian": self.ARR})
        self.assertEqual(self.C.describe(), ["qidian"])

class TestMaybeRead(unittest.TestCase):
    """v16：runner 里的空闲读书入口"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.schedule.runner as R
        import botv.life.novel as N
        self.R, self.N = R, N
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True
        self._orig_cfg = (R.cfg.last_user_msg_ts,)
        R.cfg.last_user_msg_ts = 0.0
        R._last_read_check = 0.0
        self._orig_novel = (N.fetch_rank, N.fetch_book, N.fetch_chapter)

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig
        self.R.cfg.last_user_msg_ts = self._orig_cfg[0]
        self.R._last_read_check = 0.0
        self.N.fetch_rank, self.N.fetch_book, self.N.fetch_chapter = self._orig_novel

    def _patch_novel(self):
        async def fetch_rank():
            return [("热书", "https://x/page/1")]

        async def fetch_book(url):
            return {"title": "热书", "intro": "", "chapters": [("第1章 开始", "https://x/reader/1")]}

        async def fetch_chapter(url):
            return "正文内容" * 50

        self.N.fetch_rank, self.N.fetch_book, self.N.fetch_chapter = fetch_rank, fetch_book, fetch_chapter

    def test_reads_when_idle(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        out = asyncio.run(self.R.maybe_read(now, force=True))
        self.assertTrue(out)
        data = self.store.get(str(self.R.MASTER_QQ), "")
        self.assertIn("热书", data)

    def test_night_skips(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 3, 0, tzinfo=CST)
        self.assertFalse(asyncio.run(self.R.maybe_read(now, force=True)))

    def test_throttle(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        self.assertTrue(asyncio.run(self.R.maybe_read(now, force=True)))
        # 第二次（不强制）应被节流挡掉
        self.assertFalse(asyncio.run(self.R.maybe_read(now, force=False)))

class TestNovelParse(unittest.TestCase):
    """v16：小说页解析（不联网，用合成 HTML）"""

    BOOK_HTML = """
    <h1>天外玉</h1>
    <div>作者：世沄玊靑</div>
    <div>作品简介 来自蓝星的天外之魔，不在天道管辖之内。</div>
    <a href="/reader/111">第1章 降世</a>
    <a href="/reader/222">第2章 身世</a>
    <a href="/reader/333">第3章 规则</a>
    """

    def test_parse_book(self):
        from botv.life.novel import parse_book
        info = parse_book(self.BOOK_HTML)
        self.assertEqual(info["title"], "天外玉")
        self.assertEqual(info["author"], "世沄玊靑")
        self.assertEqual(len(info["chapters"]), 3)

    def test_parse_chapter_content(self):
        from botv.life.novel import parse_chapter
        html = '<div class="muye-reader-content">' + ("正文一行\n" * 40) + "</div>"
        text = parse_chapter(html)
        self.assertGreater(len(text), 100)
        self.assertNotIn("<", text)

    def test_parse_chapter_fallback(self):
        from botv.life.novel import parse_chapter
        html = "<html><body><p>" + ("很长的一段正文内容。" * 30) + "</p></body></html>"
        self.assertGreater(len(parse_chapter(html)), 100)

    def test_parse_empty(self):
        from botv.life.novel import parse_book, parse_chapter
        self.assertIsNone(parse_book(""))
        self.assertEqual(parse_chapter(""), "")

    def test_chapter_no(self):
        from botv.life.novel import chapter_no
        self.assertEqual(chapter_no("第12章 测试"), 12)
        self.assertEqual(chapter_no("没有章号"), 0)

    def test_strip_tags(self):
        from botv.life.novel import strip_tags
        self.assertEqual(strip_tags("<p>你好<br>世界</p>"), "你好\n世界")

class TestOCR(unittest.TestCase):
    """v16：番茄正文 OCR 兜底"""

    def test_pua_ratio(self):
        from botv.life.ocr import pua_ratio
        self.assertEqual(pua_ratio("正常文本"), 0.0)
        self.assertGreater(pua_ratio("\ue000\ue001\ue002"), 0.9)
        self.assertEqual(pua_ratio(""), 0.0)

    def test_clean_removes_cjk_spaces(self):
        from botv.life.ocr import clean
        self.assertEqual(clean("云 千 珩 说 话"), "云千珩说话")
        self.assertEqual(clean("hello world"), "hello world", "英文空格要留")

    def test_clean_collapses_blank(self):
        from botv.life.ocr import clean
        self.assertEqual(clean("第一段\n\n\n\n第二段"), "第一段\n\n第二段")

    def test_fetch_chapter_prefers_ocr_on_pua(self):
        import asyncio
        import botv.life.novel as N
        import botv.life.ocr as O

        async def fake_html(url):
            return '<div class="muye-reader-content">' + ("\ue000" * 100) + "</div>"

        async def fake_ocr(url):
            return "这是一段正常的正文" * 20

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/1"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("正常", text)
        self.assertEqual(O.pua_ratio(text), 0.0)

    def test_fetch_chapter_keeps_clean_html(self):
        import asyncio
        import botv.life.novel as N
        import botv.life.ocr as O

        async def fake_html(url):
            return '<div class="muye-reader-content">' + ("正常正文" * 100) + "</div>"

        async def fake_ocr(url):
            raise AssertionError("正文干净时不该走 OCR")

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/2"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("正常正文", text)

class TestReadingFlow(unittest.TestCase):
    """v16：读书流程（注入假抓取器，不联网）"""

    def setUp(self):
        import botv.life.reading as R
        import botv.infra.repo_memory as rm
        self.R = R
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def _seed_book(self, tid="1"):
        data = self.R.load(tid)
        data["books"] = [{"title": "天外玉", "url": "https://x/page/1",
                          "last_no": 1, "last_title": "第1章", "intro": "修仙"}]
        self.R.save(tid, data)

    def _fetchers(self, chapters=3):
        async def fetch_book(url):
            return {"title": "天外玉", "intro": "修仙",
                    "chapters": [(f"第{i}章 标题", f"https://x/reader/{i}") for i in range(1, chapters + 1)]}

        async def fetch_chapter(url):
            return "正文内容" * 50

        async def summarize(text):
            return "主角逃出道观"

        return fetch_book, fetch_chapter, summarize

    def test_read_advances_progress(self):
        import asyncio
        self._seed_book()
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["chapter"], "第2章 标题")
        self.assertEqual(out["summary"], "主角逃出道观")
        data = self.R.load("1")
        self.assertEqual(data["books"][-1]["last_no"], 2)
        self.assertEqual(data["chapters"], 1)

    def test_daily_quota(self):
        import asyncio
        self._seed_book()
        data = self.R.load("1")
        self.R.mark_read(data, self.R.DAILY_CHAPTERS)
        self.R.save("1", data)
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertFalse(out["ok"])
        self.assertIn("读够", out["reason"])

    def test_night_blocks(self):
        from datetime import datetime
        from botv.config import CST
        ok, why = self.R.should_read(None, datetime(2026, 11, 9, 3, 0, tzinfo=CST))
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

    def test_idle_gate(self):
        from datetime import datetime
        from botv.config import CST
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        recent = now.timestamp() - 600
        ok, why = self.R.should_read(recent, now)
        self.assertFalse(ok, "刚聊过不读")
        old = now.timestamp() - 3 * 3600
        ok, _why = self.R.should_read(old, now)
        self.assertTrue(ok)

    def test_no_new_chapter(self):
        import asyncio
        self._seed_book()
        data = self.R.load("1")
        data["books"][-1]["last_no"] = 99
        self.R.save("1", data)
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertFalse(out["ok"])
        self.assertIn("新章节", out["reason"])

    def test_describe(self):
        self._seed_book()
        text = self.R.describe("1")
        self.assertIn("天外玉", text)
        self.assertIn("第 1 章", text)

    def test_next_chapters(self):
        chapters = [(f"第{i}章", f"u{i}") for i in range(1, 6)]
        picked = self.R.next_chapters(chapters, 2, limit=2)
        self.assertEqual([t for t, _u in picked], ["第3章", "第4章"])


    def test_pick_book(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "天外玉", "intro": "修仙", "chapters": [("第1章", "u1")]}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book = asyncio.run(self.R.pick_book(
            "9", fetch_book, Rng(), candidates=[("备用名", "https://x/page/9")]))
        self.assertEqual(book["title"], "天外玉")
        self.assertEqual(book["last_no"], 0)
        self.assertEqual(len(self.R.load("9")["books"]), 1)

    def test_pick_book_keeps_existing(self):
        import asyncio
        self._seed_book("8")
        book = asyncio.run(self.R.pick_book("8", None, None, candidates=[("别的", "https://x/page/2")]))
        self.assertEqual(book["title"], "天外玉")
        self.assertEqual(len(self.R.load("8")["books"]), 1)

    def test_pick_book_fetch_failure_uses_name(self):
        import asyncio

        async def bad(url):
            raise RuntimeError("boom")

        class Rng:
            def choice(self, seq):
                return seq[0]

        book = asyncio.run(self.R.pick_book(
            "7", bad, Rng(), candidates=[("备胎书名", "https://x/page/7")]))
        self.assertEqual(book["title"], "备胎书名")

    def test_book_candidates_env(self):
        import os
        old = os.environ.get("NAO_BOOK_URLS")
        os.environ["NAO_BOOK_URLS"] = "我的书|https://x/page/1,https://x/page/2"
        try:
            items = self.R.book_candidates()
        finally:
            if old is None:
                os.environ.pop("NAO_BOOK_URLS", None)
            else:
                os.environ["NAO_BOOK_URLS"] = old
        self.assertEqual(items[0], ("我的书", "https://x/page/1"))
        self.assertEqual(items[1][1], "https://x/page/2")


    def test_detect_url(self):
        got = self.R.detect_book_request("去看 https://fanqienovel.com/page/123 这本")
        self.assertEqual(got["url"], "https://fanqienovel.com/page/123")

    def test_detect_title(self):
        got = self.R.detect_book_request("《天外玉》你去看看")
        self.assertEqual(got["title"], "天外玉")

    def test_detect_none(self):
        self.assertIsNone(self.R.detect_book_request("今天天气不错"))
        self.assertIsNone(self.R.detect_book_request("《天外玉》好看吗"))  # 没有「去看」意图

    def test_follow_by_url(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "新书", "intro": "简介", "chapters": []}

        book, msg = asyncio.run(self.R.follow("5", url="https://x/page/5", fetch_book=fetch_book))
        self.assertEqual(book["title"], "新书")
        self.assertIn("好，我去看", msg)
        self.assertEqual(len(self.R.load("5")["books"]), 1)

    def test_follow_twice(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "新书", "intro": "", "chapters": []}

        asyncio.run(self.R.follow("6", url="https://x/page/6", fetch_book=fetch_book))
        book, msg = asyncio.run(self.R.follow("6", url="https://x/page/6", fetch_book=fetch_book))
        self.assertIn("已经在追", msg)
        self.assertEqual(len(self.R.load("6")["books"]), 1)

    def test_follow_by_title_needs_link(self):
        import asyncio
        book, msg = asyncio.run(self.R.follow("4", title="天外玉"))
        self.assertIsNone(book)
        self.assertIn("链接", msg)


    def test_parse_rank(self):
        from botv.life.novel import parse_rank
        html = ('<a href="/page/111"><h3>部族荣光</h3><p>丧狐</p></a>'
                '<a href="/page/222"><h3>莫若凌霄</h3></a>'
                '<a href="/page/111"><h3>重复的</h3></a>'
                '<a href="/writer/zone/article/1"><h3>公告</h3></a>')
        items = parse_rank(html)
        self.assertEqual(items[0], ("部族荣光", "https://fanqienovel.com/page/111"))
        self.assertEqual(len(items), 2, "去重且只收 /page/ 链接")

    def test_parse_rank_limit(self):
        from botv.life.novel import parse_rank
        html = "".join(f'<a href="/page/{i}"><h3>书{i}</h3></a>' for i in range(30))
        self.assertEqual(len(parse_rank(html, limit=5)), 5)

    def test_parse_rank_empty(self):
        from botv.life.novel import parse_rank
        self.assertEqual(parse_rank(""), [])
        self.assertEqual(parse_rank("<div>没有书</div>"), [])


    def test_pick_from_rank(self):
        import asyncio

        async def fetch_rank():
            return [("热书A", "https://x/page/a"), ("热书B", "https://x/page/b")]

        async def fetch_book(url):
            return {"title": "热书A", "intro": "简介", "chapters": []}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book, msg = asyncio.run(self.R.pick_from_rank(
            "10", fetch_rank, fetch_book, Rng()))
        self.assertIsNotNone(book)
        self.assertEqual(book["title"], "热书A")
        self.assertIn("我在看", msg)

    def test_pick_from_rank_keeps_existing(self):
        import asyncio
        self._seed_book("11")
        book, msg = asyncio.run(self.R.pick_from_rank("11", lambda: None, None, None))
        self.assertEqual(book["title"], "天外玉")
        self.assertIn("已经在追", msg)

    def test_pick_from_rank_empty(self):
        import asyncio

        async def empty():
            return []

        book, msg = asyncio.run(self.R.pick_from_rank("12", empty, None, None))
        self.assertIsNone(book)
        self.assertIn("热榜", msg)

    def test_pick_from_rank_exclude(self):
        import asyncio

        async def fetch_rank():
            return [("看过的", "https://x/page/old"), ("新书", "https://x/page/new")]

        async def fetch_book(url):
            return {"title": "新书", "intro": "", "chapters": []}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book, _msg = asyncio.run(self.R.pick_from_rank(
            "13", fetch_rank, fetch_book, Rng(),
            exclude=[("看过的", "https://x/page/old")]))
        self.assertEqual(book["url"], "https://x/page/new")


    def test_summarize_with_model(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "云千珩逃出道观，被追兵盯上。"

        out = asyncio.run(self.R.summarize_chapter("正文" * 200, call_model=fake_model))
        self.assertEqual(out, "云千珩逃出道观，被追兵盯上。")

    def test_summarize_strips_prefix(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "摘要：他进了城。"

        out = asyncio.run(self.R.summarize_chapter("正文", call_model=fake_model))
        self.assertEqual(out, "他进了城。")

    def test_summarize_truncates(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "啊" * 500

        out = asyncio.run(self.R.summarize_chapter("正文", call_model=fake_model))
        self.assertLessEqual(len(out), self.R.SUMMARY_MAX)

    def test_summarize_fallback_on_error(self):
        import asyncio

        async def boom(msgs, max_tokens=0):
            raise RuntimeError("api down")

        out = asyncio.run(self.R.summarize_chapter("第一句。第二句。第三句。", call_model=boom))
        self.assertIn("第一句", out)

    def test_summarize_empty(self):
        import asyncio
        self.assertEqual(asyncio.run(self.R.summarize_chapter("")), "")
        self.assertEqual(asyncio.run(self.R.summarize_chapter("   ")), "")

    def test_fallback_summary(self):
        out = self.R.fallback_summary("他推开门。外面在下雨。远处有人喊他。")
        self.assertIn("他推开门", out)
        self.assertNotIn("远处有人喊他", out, "只取前两句")


    def test_follow_request_ack(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "天外玉", "intro": "", "chapters": []}

        msg = asyncio.run(self.R.follow_request(
            "20", {"url": "https://x/page/1", "title": ""}, fetch_book=fetch_book))
        self.assertIn("好，我去看", msg)
        self.assertEqual(self.R.load("20")["books"][0]["url"], "https://x/page/1")

    def test_follow_request_title_only(self):
        import asyncio
        msg = asyncio.run(self.R.follow_request("21", {"url": "", "title": "没有的书"}))
        self.assertIn("链接", msg)

    def test_follow_request_empty(self):
        import asyncio
        self.assertEqual(asyncio.run(self.R.follow_request("22", None)), "")

class TestReadingPrompt(unittest.TestCase):
    """v16：把「她在看什么」注入 prompt"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def test_describe_empty(self):
        from botv.life.reading import describe
        self.assertEqual(describe("nobody"), "")

    def test_describe_with_book(self):
        import json
        from botv.life.reading import describe
        self.store["1"] = json.dumps({"books": [{"title": "天外玉", "url": "u", "last_no": 12}]})
        text = describe("1")
        self.assertIn("天外玉", text)
        self.assertIn("12", text)

    def test_prompt_has_reading_slot(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        text = get_system_prompt()
        self.assertIn("你最近在看", text)

    def test_prompt_uses_placeholder(self):
        from botv.ai.persona import LOCAL_SYSTEM_PROMPT
        self.assertIn("{reading}", LOCAL_SYSTEM_PROMPT)

class TestSharePoints(unittest.TestCase):
    """v16-E8：攒够几个点再分享"""

    def setUp(self):
        self.data = {"books": [{"title": "天外玉", "url": "u", "last_no": 5}],
                     "pending": [], "day": "", "chapters": 0}

    def test_not_ready_before_three(self):
        self.R = __import__("botv.life.reading", fromlist=["x"])
        for i in range(2):
            self.R.note_summary(self.data, f"第{i}个点")
        self.assertFalse(self.R.share_ready(self.data))

    def test_ready_after_three(self):
        from botv.life.reading import note_summary, share_ready
        for i in range(3):
            note_summary(self.data, f"第{i}个点")
        self.assertTrue(share_ready(self.data))

    def test_build_share_has_title(self):
        from botv.life.reading import note_summary, build_share
        for i in range(3):
            note_summary(self.data, f"第{i}个点")
        text = build_share(self.data)
        self.assertIn("天外玉", text)
        self.assertIn("第0个点", text)

    def test_mark_shared_clears(self):
        from botv.life.reading import note_summary, mark_shared
        for i in range(4):
            note_summary(self.data, f"第{i}个点")
        mark_shared(self.data)
        self.assertEqual(len(self.data["pending"]), 1, "用掉 3 个，剩 1 个")
        self.assertGreater(self.data["last_share_ts"], 0)

    def test_cooldown(self):
        import time
        from botv.life.reading import note_summary, share_ready
        for i in range(3):
            note_summary(self.data, f"点{i}")
        self.data["last_share_ts"] = time.time() - 60
        self.assertFalse(share_ready(self.data), "3 小时内不重复分享")

    def test_summary_capped(self):
        from botv.life.reading import note_summary
        note_summary(self.data, "长" * 500)
        self.assertLessEqual(len(self.data["pending"][0]), 100)

class TestShareReading(unittest.TestCase):
    """v16-E8：攒够点后主动分享"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.schedule.runner as R
        self.R = R
        self.sent, self.prompts = [], []
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True
        self._orig_fn = (R.get_character_reply, R.send_short_reply)
        self._seed()

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig
        self.R.get_character_reply, self.R.send_short_reply = self._orig_fn

    def _seed(self, pending=3):
        import json
        data = {"books": [{"title": "天外玉", "url": "u", "last_no": 5}],
                "pending": [f"第{i}个点" for i in range(pending)],
                "day": "", "chapters": 0, "last_share_ts": 0}
        self.store[str(self.R.MASTER_QQ)] = json.dumps(data)

    def _patch(self, ret="她还记得那章，随口提了一句"):
        async def fake_reply(prompt, tid):
            self.prompts.append(prompt)
            return ret

        async def fake_send(*a, **k):
            self.sent.append(a)

        self.R.get_character_reply = fake_reply
        self.R.send_short_reply = fake_send

    def test_share_sends(self):
        import asyncio
        self._patch()
        self.assertTrue(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("天外玉", self.prompts[0])

    def test_share_needs_three_points(self):
        import asyncio
        self._seed(pending=2)
        self._patch()
        self.assertFalse(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(self.sent, [])

    def test_share_clears_points(self):
        import asyncio, json
        self._patch()
        asyncio.run(self.R.maybe_share_reading())
        data = json.loads(self.store[str(self.R.MASTER_QQ)])
        self.assertEqual(len(data["pending"]), 0)
        self.assertGreater(data["last_share_ts"], 0)

    def test_share_skips_fallback(self):
        import asyncio
        from botv.core.types import Fallback
        self._patch(ret=Fallback("挂了"))
        self.assertFalse(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(self.sent, [])

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
