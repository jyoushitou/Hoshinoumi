# ===================== v24.1 番茄搜索 =====================
import asyncio
import unittest


SAMPLE = '''
<html><body>
<a href="/page/7143038691944959011">十日终焉</a>
<script>window.__DATA__={"bookName":"十日终焉","bookId":"7143038691944959011"}</script>
</body></html>
'''


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
