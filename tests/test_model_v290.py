# ===================== v29.0 模型层契约 =====================
import unittest

from bot.ports.models import (
    ModelProvider, ModelReply, ModelRequest,
)


class TestModelContract(unittest.TestCase):
    def test_request_defaults(self):
        r = ModelRequest(messages=[{"role": "user", "content": "hi"}])
        self.assertEqual(r.max_tokens, None)
        self.assertEqual(r.target_id, "")

    def test_fake_provider(self):
        class P:
            name = "demo"

            def capabilities(self):
                return {"text"}

            async def complete(self, req):
                return ModelReply(text="ok", model=self.name)

        p = P()
        self.assertIsInstance(p, ModelProvider)
        self.assertEqual(p.capabilities(), {"text"})


if __name__ == "__main__":
    unittest.main()
