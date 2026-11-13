# ===================== v21.8 缓存命名空间 =====================
import unittest


class TestCacheNamespace(unittest.TestCase):
    def test_namespace_isolated_and_invalidated(self):
        from bot.infra import cache

        a = cache.namespace("test:a")
        b = cache.namespace("test:b")
        a.set("k", 1, ttl=60)
        b.set("k", 2, ttl=60)
        self.assertEqual(a.get("k"), 1)
        self.assertEqual(b.get("k"), 2)
        a.invalidate()
        self.assertIsNone(a.get("k"))
        self.assertEqual(b.get("k"), 2)
        b.invalidate()

    def test_diary_cache_uses_shared_ttl(self):
        from bot.diary import cache as diary_cache

        diary_cache.clear()
        diary_cache.put("2026-11-13", "今天很好")
        self.assertEqual(diary_cache.get("2026-11-13"), "今天很好")
        self.assertEqual(diary_cache.peek("2026-11-13"), "今天很好")
        diary_cache.clear()
        self.assertIsNone(diary_cache.get("2026-11-13"))


if __name__ == "__main__":
    unittest.main()
