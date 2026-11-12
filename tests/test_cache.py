# ===================== v18.13 进程内 TTL 缓存 =====================

import unittest
from unittest.mock import patch

from botv.infra import cache


class TestCache(unittest.TestCase):
    def setUp(self):
        cache.invalidate()
        cache.reset_stats()
        self.now = [1000.0]

    def test_get_set(self):
        with patch.object(cache, "_now", lambda: self.now[0]):
            cache.set("a", 1, ttl=5)
            self.assertEqual(cache.get("a"), 1)

    def test_expire(self):
        with patch.object(cache, "_now", lambda: self.now[0]):
            cache.set("a", 1, ttl=5)
            self.now[0] += 6
            self.assertIsNone(cache.get("a"))

    def test_invalidate_prefix(self):
        cache.set("cron:1", 1, 5)
        cache.set("cron:2", 2, 5)
        cache.set("other", 3, 5)
        cache.invalidate("cron:")
        self.assertIsNone(cache.get("cron:1"))
        self.assertIsNone(cache.get("cron:2"))
        self.assertEqual(cache.get("other"), 3)

    def test_stats(self):
        cache.set("a", 1, 5)
        cache.get("a")
        cache.get("missing")
        s = cache.stats()
        self.assertEqual(s["hits"], 1)
        self.assertEqual(s["misses"], 1)


class TestCountsCache(unittest.TestCase):
    def test_counts_cached(self):
        from botv.infra import repo_query

        cache.invalidate()
        calls = []

        def fake_count(table, cursor=None):
            calls.append(table)
            return 1

        tables = ["logs", "events"]
        with patch.object(repo_query, "count_table", fake_count):
            a = repo_query.counts(tables)
            b = repo_query.counts(tables)
        self.assertEqual(a, b)
        self.assertEqual(len(calls), 2, "第二次应命中缓存")

    def test_cursor_bypasses_cache(self):
        from botv.infra import repo_query

        cache.invalidate()
        calls = []

        def fake_count(table, cursor=None):
            calls.append(cursor)
            return 1

        with patch.object(repo_query, "count_table", fake_count):
            repo_query.counts(["logs"], cursor=object())
            repo_query.counts(["logs"], cursor=object())
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
