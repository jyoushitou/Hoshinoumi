# ===================== v24.5 HAR 脱敏 =====================
import json
import tempfile
import unittest
from pathlib import Path


class TestSanitizeHar(unittest.TestCase):
    def test_redacts_headers_query_and_body(self):
        from scripts.sanitize_har import sanitize
        har = {"log": {"entries": [{
            "request": {
                "method": "GET",
                "url": "https://example.com/api/chapter?book=1&token=SECRET",
                "headers": [{"name": "Cookie", "value": "sid=SECRET"},
                             {"name": "Accept", "value": "*/*"}],
            },
            "response": {"status": 200,
                         "headers": [{"name": "Set-Cookie", "value": "sid=SECRET"}],
                         "content": {"mimeType": "text/html",
                                     "text": "受版权保护的正文"}},
        }]}}
        clean, endpoints = sanitize(har)
        s = json.dumps(clean, ensure_ascii=False)
        self.assertNotIn("SECRET", s)
        self.assertNotIn("受版权保护的正文", s)
        self.assertEqual(endpoints[0]["status"], 200)
        self.assertIn("token=%5BREDACTED%5D", s)


if __name__ == "__main__":
    unittest.main()
