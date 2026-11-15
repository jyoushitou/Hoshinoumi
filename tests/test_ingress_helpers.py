# ===================== v25.5 ingress 辅助 =====================
import unittest


class TestIngressHelpers(unittest.TestCase):
    def test_hop_headers_filtered(self):
        from bot.ingress import _headers

        class Req:
            headers = {"Host": "x", "Connection": "keep-alive",
                       "Authorization": "Bearer t", "X-Test": "1"}

        h = _headers(Req())
        self.assertNotIn("Host", h)
        self.assertNotIn("Connection", h)
        self.assertEqual(h["Authorization"], "Bearer t")
        self.assertEqual(h["X-Test"], "1")


if __name__ == "__main__":
    unittest.main()
