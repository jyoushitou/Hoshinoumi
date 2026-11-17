# ===================== v34.2.0.1 情境 reporter =====================
import unittest

from bot.life.presence_reporter import classify


class TestReporterV3421(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("Visual Studio Code"),"coding")
        self.assertEqual(classify("Zoom Meeting"),"meeting")
        self.assertEqual(classify("bilibili"),"video")
        self.assertEqual(classify("unknown app"),"unknown")


if __name__=="__main__": unittest.main()
