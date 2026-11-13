# ===================== v19.5.6 API 配置向导 =====================
import unittest

from scripts.configure_api import _mask


class TestConfigureApi(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(_mask(""), "（未配置）")
        self.assertEqual(_mask("12345678"), "12***")
        self.assertEqual(_mask("sk-1234567890"), "sk-1...90")


if __name__ == "__main__":
    unittest.main()
