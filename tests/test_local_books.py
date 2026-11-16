# ===================== v24.6 本地 TXT/EPUB =====================
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path


def _stub():
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m


_stub()


class TestLocalBooks(unittest.TestCase):
    def setUp(self):
        from bot.life import local_books as LB
        self.LB = LB
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = LB.BOOK_DIR
        LB.BOOK_DIR = Path(self.tmp.name)
        LB._progress.clear()
        LB._declared.clear()

    def tearDown(self):
        self.LB.BOOK_DIR = self.orig
        self.tmp.cleanup()

    def _txt(self):
        p = self.LB.BOOK_DIR / "测试书.txt"
        p.write_text("第1章 开始\n正文一\n第2章 继续\n正文二\n", encoding="utf-8")
        return p

    def test_txt_chapters_and_read(self):
        self._txt()
        title, chapters = self.LB.load_book("测试书")
        self.assertEqual(title, "测试书")
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0][0], "全文")
        info = self.LB.read_chapter("测试书", 1)
        self.assertIn("正文二", info["text"])

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            self.LB._safe_name("../etc/passwd")

    def test_epub(self):
        p = self.LB.BOOK_DIR / "书.epub"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("META-INF/container.xml",
                       '<?xml version="1.0"?><container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
            z.writestr("OEBPS/content.opf",
                       '<?xml version="1.0"?><package><metadata><title>EPUB 书名</title></metadata>'
                       '<manifest><item id="c1" href="c1.xhtml"/></manifest>'
                       '<spine><itemref idref="c1"/></spine></package>')
            z.writestr("OEBPS/c1.xhtml", "<html><body><p>EPUB 正文内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容</p></body></html>")
        title, chapters = self.LB.load_book("书")
        self.assertEqual(title, "EPUB 书名")
        self.assertTrue(chapters)
        self.assertIn("EPUB 正文", chapters[0][1])

    def test_declaration_once(self):
        a = self.LB.declaration_once("u1")
        b = self.LB.declaration_once("u1")
        self.assertIn("本地阅读", a)
        self.assertEqual(b, "")

    def test_local_command_returns_fast_ack(self):
        import asyncio
        from bot.cmd import books_cmd
        from bot.cmd.registry import CommandContext
        from bot.life import book_queue as BQ
        self._txt()
        orig_enq = BQ.enqueue
        orig_spawn = books_cmd._spawn
        calls = {}
        BQ.enqueue = lambda uid, name, total=0: calls.setdefault("enqueue", name) or True
        books_cmd._spawn = lambda coro: (calls.setdefault("spawn", True), coro.close())
        try:
            ctx = CommandContext(parts=["book", "local", "测试书"], uid="u1",
                                 ws=None, is_group=False, gid=0)
            out = asyncio.run(books_cmd.cmd_book(ctx))
        finally:
            BQ.enqueue = orig_enq
            books_cmd._spawn = orig_spawn
        self.assertIn("正在解析全书首个 1000 字", out)
        self.assertEqual(calls["enqueue"], "测试书")
        self.assertTrue(calls["spawn"])

    def test_read_first_background(self):
        import asyncio
        from bot.cmd import books_cmd
        from bot.cmd.registry import CommandContext
        from bot.life import book_queue as BQ
        self._txt()
        orig = (BQ.set_total, BQ.set_progress, BQ.mark_error)
        calls = {}
        BQ.set_total = lambda uid, name, total: calls.setdefault("total", total)
        BQ.set_progress = lambda uid, name, chapter, total=0, **kw: calls.update(
            {"chapter": chapter, "offset": kw.get("offset")})
        BQ.mark_error = lambda uid, name: None
        import bot.chat.send as S
        from bot.life import reading
        orig_send = S.send_short_reply
        orig_sum = reading.summarize_chapter
        sent = []
        async def fake_send(*args, **kwargs):
            sent.append(args[1] if len(args) > 1 else "")
        async def fake_sum(text, **kwargs):
            return "测试摘要"
        S.send_short_reply = fake_send
        reading.summarize_chapter = fake_sum
        try:
            ctx = CommandContext(parts=["book", "local", "测试书"], uid="u1",
                                 ws=None, is_group=False, gid=0)
            asyncio.run(books_cmd._read_first_and_notify(ctx, "测试书"))
        finally:
            BQ.set_total, BQ.set_progress, BQ.mark_error = orig
            S.send_short_reply = orig_send
            reading.summarize_chapter = orig_sum
        self.assertEqual(calls["chapter"], 1)
        self.assertGreater(calls["offset"], 0)
        self.assertEqual(sent, [], "v29.4 自动首读不应发聊天")

    def test_read_chunk_1000_chars(self):
        p = self.LB.BOOK_DIR / "长章.txt"
        p.write_text("第1章 长章\n" + ("字" * 2500), encoding="utf-8")
        first = self.LB.read_chunk("长章", 0)
        self.assertEqual(len(first["chunk"]), 1000)
        self.assertEqual(first["next_offset"], 1000)
        second = self.LB.read_chunk("长章", first["next_offset"])
        self.assertEqual(len(second["chunk"]), 1000)
        third = self.LB.read_chunk("长章", second["next_offset"])
        self.assertGreater(len(third["chunk"]), 0)
        self.assertTrue(third["done"])

    def test_first_char_is_file_start(self):
        p = self.LB.BOOK_DIR / "开头.txt"
        p.write_text("<刀剑神域>\n第一卷 艾恩葛朗特\n第八章 中央圣堂\n正文", encoding="utf-8")
        first = self.LB.read_chunk("开头", 0)
        self.assertTrue(first["chunk"].startswith("<刀剑神域>"))
        self.assertIn("第一卷", first["chunk"])
        self.assertEqual(first["chapter"], "全文")

    def test_summary_no_raw_text_fallback(self):
        import asyncio
        from bot.life import reading
        async def empty(msgs, max_tokens=None):
            return ""
        out = asyncio.run(reading.summarize_chapter(
            "<刀剑神域>正文", call_model=empty, allow_text_fallback=False))
        self.assertEqual(out, "")

    def test_book_summary_memory(self):
        from bot.life import book_memory
        orig = book_memory.add_event_to_db
        calls = []
        book_memory.add_event_to_db = lambda *a, **kw: calls.append((a, kw))
        try:
            info = {"offset": 1000, "chars": 1000}
            book_memory.remember_chunk("u1", "u1", "书", info, "摘要")
            book_memory.remember_finished("u1", "u1", "书", 12000)
        finally:
            book_memory.add_event_to_db = orig
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1]["kind"], "book")
        self.assertIn("摘要", calls[0][0][1])
        self.assertIn("读完", calls[1][0][1])

    def test_command_group_silent(self):
        from bot.cmd.books_cmd import cmd_book
        from bot.cmd.registry import CommandContext
        ctx = CommandContext(parts=["book", "read", "x"], uid="u1",
                             ws=None, is_group=True, gid=1)
        import asyncio
        self.assertEqual(asyncio.run(cmd_book(ctx)), "")


if __name__ == "__main__":
    unittest.main()



