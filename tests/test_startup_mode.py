# ===================== v25.7 启动/热更提示 =====================
import os
import unittest
from unittest import mock


class TestStartupMode(unittest.TestCase):
    def test_first(self):
        from bot.core import startup
        with mock.patch("bot.infra.repo_meta.get_value", side_effect=lambda k, default=None: {
            "first_start": None, "version": None}.get(k, default)), \
             mock.patch.object(startup, "get_version", lambda: "v25.7.0"):
            mode, prev, cur = startup.detect()
        self.assertEqual(mode, "first")
        self.assertEqual(prev, "")

    def test_hot_when_worker_version_differs(self):
        from bot.core import startup
        with mock.patch("bot.infra.repo_meta.get_value", side_effect=lambda k, default=None: {
            "first_start": "2026-01-01", "version": "v25.6.2"}.get(k, default)), \
             mock.patch.object(startup, "get_version", lambda: "v25.7.0"), \
             mock.patch.dict(os.environ, {"NAO_WORKER_VERSION": "25.7.0"}):
            mode, prev, cur = startup.detect()
        self.assertEqual(mode, "hot")
        self.assertEqual(prev, "v25.6.2")

    def test_normal_when_same_version(self):
        from bot.core import startup
        with mock.patch("bot.infra.repo_meta.get_value", side_effect=lambda k, default=None: {
            "first_start": "2026-01-01", "version": "v25.7.0"}.get(k, default)), \
             mock.patch.object(startup, "get_version", lambda: "v25.7.0"), \
             mock.patch.dict(os.environ, {"NAO_WORKER_VERSION": "25.7.0"}):
            mode, _, _ = startup.detect()
        self.assertEqual(mode, "normal")

    def test_notice_texts_differ(self):
        from bot.chat.online import notice_text
        first = notice_text("first", "v25.7.0")
        hot = notice_text("hot", "v25.7.0")
        normal = notice_text("normal", "v25.7.0")
        self.assertIn("第一次上线", first)
        self.assertIn("热更新完成", hot)
        self.assertNotEqual(first, hot)
        self.assertNotEqual(hot, normal)


if __name__ == "__main__":
    unittest.main()
