# ===================== v26.0 WS token =====================
import os
import unittest
from unittest import mock

from bot.chat.ws_auth import token_ok


class TestWsAuth(unittest.TestCase):
    def test_disabled(self):
        with mock.patch.dict(os.environ, {"NAO_WS_TOKEN": ""}):
            self.assertTrue(token_ok("/?token=whatever"))

    def test_match(self):
        with mock.patch.dict(os.environ, {"NAO_WS_TOKEN": "s3cret"}):
            self.assertTrue(token_ok("/?token=s3cret"))
            self.assertFalse(token_ok("/?token=bad"))
            self.assertFalse(token_ok("/"))
            self.assertFalse(token_ok(""))


if __name__ == "__main__":
    unittest.main()
