# ===================== v24.6 本地 TXT/EPUB =====================
import tempfile
import unittest
import zipfile
from pathlib import Path


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
        self.assertEqual(len(chapters), 2)
        info = self.LB.read_chapter("测试书", 2)
        self.assertEqual(info["index"], 2)
        self.assertIn("正文二", info["summary"])

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

    def test_command_group_silent(self):
        from bot.cmd.books_cmd import cmd_book
        from bot.cmd.registry import CommandContext
        ctx = CommandContext(parts=["book", "read", "x"], uid="u1",
                             ws=None, is_group=True, gid=1)
        import asyncio
        self.assertEqual(asyncio.run(cmd_book(ctx)), "")


if __name__ == "__main__":
    unittest.main()

