# ===================== v24.1 番茄搜索 =====================
import asyncio
import unittest


SAMPLE = '''
<html><body>
<a href="/page/7143038691944959011">十日终焉</a>
<script>window.__DATA__={"bookName":"十日终焉","bookId":"7143038691944959011"}</script>
</body></html>
'''


class TestTitleV242(unittest.TestCase):
    HTML_A = """<html><head><title>十日终焉完整版在线免费阅读_番茄小说官网</title></head>
    <body><h1>十日终焉</h1><div>作者：杀虫队队员</div>
    <div>作品简介 无限流</div><div>已完结 320.1 万字</div>
    <a href="/reader/1">第1章 开端</a></body></html>"""

    HTML_B = """<html><head><title>领主：我在苦痛世界，养成少女 - 番茄小说</title></head>
    <body><h1>领主：我在苦痛世界，养成少女</h1></body></html>"""

    def test_real_titles(self):
        from bot.life import novel
        a = novel.parse_book(self.HTML_A)
        b = novel.parse_book(self.HTML_B)
        self.assertEqual(a["title"], "十日终焉")
        self.assertEqual(b["title"], "领主：我在苦痛世界，养成少女")
        self.assertEqual(a["author"], "杀虫队队员")
        self.assertEqual(a["status"], "完结")

    def test_title_clean_suffix(self):
        from bot.life.novel import clean_book_title
        self.assertEqual(clean_book_title("十日终焉完整版在线免费阅读_番茄小说官网"), "十日终焉")

    def test_no_fake_title(self):
        import asyncio
        from bot.life import reading
        orig = reading.load
        reading.load = lambda tid, user_id="__owner__": {"books": []}
        try:
            async def fetch(url):
                return {"title": "", "chapters": []}
            book, msg = asyncio.run(reading.follow("99", url="https://x/page/1", fetch_book=fetch))
        finally:
            reading.load = orig
        self.assertIsNotNone(book)
        self.assertEqual(book["title"], "")
        self.assertIn("没有乱编书名", msg)


class TestProgressV243(unittest.TestCase):
    def test_first_read_starts_chapter_one(self):
        import asyncio
        from bot.life import reading
        data = {"books": [{"title": "A", "url": "u", "last_no": 0}],
                "day": "", "chapters": 0}
        orig_load, orig_save = reading.load, reading.save
        reading.load = lambda tid, user_id="__owner__": data
        reading.save = lambda tid, d, user_id="__owner__": True

        async def fetch_book(url):
            return {"title": "A", "chapters": [("第1章 开始", "c1"), ("第2章", "c2")]}

        async def fetch_chapter(url):
            return "正文" * 100

        try:
            out = asyncio.run(reading.read_once("1", fetch_book, fetch_chapter, force=True))
        finally:
            reading.load, reading.save = orig_load, orig_save
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["chapter"], "第1章 开始")

    def test_no_chapters_reason(self):
        import asyncio
        from bot.life import reading
        data = {"books": [{"title": "A", "url": "u", "last_no": 0}], "day": "", "chapters": 0}
        orig_load, orig_save = reading.load, reading.save
        reading.load = lambda tid, user_id="__owner__": data
        reading.save = lambda tid, d, user_id="__owner__": True

        async def fetch_book(url):
            return {"title": "A", "chapters": []}

        try:
            out = asyncio.run(reading.read_once("1", fetch_book, lambda u: None, force=True))
        finally:
            reading.load, reading.save = orig_load, orig_save
        self.assertIn("目录为空", out["reason"])


class TestSearchV241(unittest.TestCase):
    def test_parse_ssr_and_json(self):
        from bot.life import novel
        items = novel.parse_search(SAMPLE)
        self.assertTrue(items)
        self.assertEqual(items[0][0], "十日终焉")
        self.assertIn("7143038691944959011", items[0][1])

    def test_search_book_uses_q(self):
        from bot.life import novel
        orig = novel.fetch_html

        async def fake(url):
            return SAMPLE

        novel.fetch_html = fake
        try:
            hit = asyncio.run(novel.search_book("十日终焉"))
        finally:
            novel.fetch_html = orig
        self.assertIsNotNone(hit)
        self.assertEqual(hit[0], "十日终焉")

    def test_search_empty(self):
        from bot.life import novel
        orig = novel.fetch_html

        async def fake(url):
            return "<html><body>无结果</body></html>"

        novel.fetch_html = fake
        try:
            self.assertIsNone(asyncio.run(novel.search_book("不存在")))
        finally:
            novel.fetch_html = orig


if __name__ == "__main__":
    unittest.main()
