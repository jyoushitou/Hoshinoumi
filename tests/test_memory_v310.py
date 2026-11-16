# ===================== v31.0 记忆层契约 =====================
import unittest

from bot.ports.memory import MemoryItem, MemoryStore, Retriever


class FakeStore:
    async def add(self, user_id, item):
        return "id1"

    async def delete(self, user_id, item_id):
        return None

    async def recent(self, user_id, n):
        return []


class FakeRetriever:
    async def search(self, user_id, query, top_k=5):
        return []


class TestMemoryContract(unittest.TestCase):
    def test_store_protocol(self):
        self.assertIsInstance(FakeStore(), MemoryStore)

    def test_retriever_protocol(self):
        self.assertIsInstance(FakeRetriever(), Retriever)

    def test_item(self):
        item = MemoryItem(target_id="t", kind="event", content="x")
        self.assertEqual(item.content, "x")


if __name__ == "__main__":
    unittest.main()
