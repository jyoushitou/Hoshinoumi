# ===================== v19.5.6 API 配置向导 =====================
import unittest
from unittest import mock

import scripts.configure_api as C
from scripts.configure_api import _mask


class TestConfigureApi(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(_mask(""), "（未配置）")
        self.assertEqual(_mask("12345678"), "12***")
        self.assertEqual(_mask("sk-1234567890"), "sk-1...90")

    def test_show_input_visible(self):
        old = C.SHOW_INPUT
        C.SHOW_INPUT = True
        try:
            with mock.patch("builtins.input", return_value="sk-test"):
                self.assertEqual(C._ask("Key", "", secret=True), "sk-test")
        finally:
            C.SHOW_INPUT = old


if __name__ == "__main__":
    unittest.main()
