# ===================== v18.11 情绪跨天 =====================

import sys
import types
import unittest
from unittest.mock import patch


def _stub_missing_deps():
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)


_stub_missing_deps()


class TestEmotionPersist(unittest.TestCase):
    def test_tick_half_life(self):
        from botv.life import state

        s = state.default_state()
        s["emotion"] = "难过"
        s["emotion_power"] = 0.5    # 普通强度：3 天半衰
        s = state.tick(s, 24 * 3)   # 3 天
        self.assertAlmostEqual(s["emotion_power"], 0.25, places=2)

    def test_strong_half_life_five_days(self):
        from botv.life import state

        s = state.default_state()
        s["emotion"] = "生气"
        s["emotion_power"] = 1.0
        s = state.tick(s, 24 * 3)   # 强烈：5 天半衰
        self.assertGreater(s["emotion_power"], 0.6)

    def test_detect_prefers_stored(self):
        from botv.speech import voice

        fake = {"mood": 0.9, "emotion": "难过", "emotion_power": 0.5}
        with patch("botv.life.state.current", return_value=fake):
            self.assertEqual(voice.detect_emotion(), "难过")

    def test_detect_reinfers_when_weak(self):
        from botv.speech import voice

        fake = {"mood": 0.9, "emotion": "难过", "emotion_power": 0.05}
        with patch("botv.life.state.current", return_value=fake), \
                patch("botv.life.state.remember_emotion", return_value=fake):
            self.assertEqual(voice.detect_emotion(), "开心")


if __name__ == "__main__":
    unittest.main()
