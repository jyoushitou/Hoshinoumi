# ===================== v25.1 热加载 =====================
import unittest
from unittest import mock


class TestHotReload(unittest.TestCase):
    def test_changed_detects_modify_add_remove(self):
        from bot.core import hot_reload as H
        a = {"a": (1, 10), "b": (2, 20)}
        self.assertFalse(H.changed(a, dict(a)))
        self.assertTrue(H.changed(a, {"a": (3, 10), "b": (2, 20)}))
        self.assertTrue(H.changed(a, {"a": (1, 10), "b": (2, 20), "c": (3, 1)}))
        self.assertTrue(H.changed(a, {"a": (1, 10)}))

    def test_reload_now_calls_config_and_persona(self):
        from bot.core import hot_reload as H
        calls = []
        with mock.patch.object(H.appconfig, "reload", lambda: calls.append("config")), \
             mock.patch("bot.ai.prompt.reload_personality_supplement",
                        lambda: calls.append("persona")):
            H.reload_now()
        self.assertEqual(calls, ["config", "persona"])


if __name__ == "__main__":
    unittest.main()
