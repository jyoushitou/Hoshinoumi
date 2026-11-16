# ===================== v31.2 BM25Retriever =====================
import asyncio
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.memory.bm25_retriever import BM25Retriever
from bot.ports.memory import Retriever


class TestBM25Retriever(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(BM25Retriever(), Retriever)

    def test_search_scoped_and_score(self):
        mem = {"id": 1, "summary": "x", "tags": "t"}
        with mock.patch("bot.memory.bm25_retriever.load_memories_for_search",
                        return_value=[mem]) as load, \
             mock.patch("bot.memory.bm25_retriever.retrieve",
                        return_value=[(mem, 0.5)]):
            out = asyncio.run(BM25Retriever().search("u1", "x", 3))
        load.assert_called_once_with("u1", limit=300, user_id="u1")
        self.assertEqual(out[0]["score"], 0.5)
        self.assertEqual(out[0]["summary"], "x")


if __name__ == "__main__":
    unittest.main()
