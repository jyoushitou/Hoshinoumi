# ===================== 语音情感与声线测试（v17.12） =====================

import asyncio
import os
import shutil
import sys
import types
import unittest


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


class TestProfile(unittest.TestCase):
    """声纹档案：读写、缺失回落、坏文件不炸"""

    def setUp(self):
        from bot.speech import voice

        self.V = voice
        self.dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".tmp", f"voice-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "voice.json")
        self._orig = self.V.profile_path
        self.V.profile_path = lambda persona=None: self.path

    def tearDown(self):
        self.V.profile_path = self._orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_default_when_missing(self):
        prof = self.V.load_profile()
        self.assertEqual(prof["pitch_base"], 0)
        self.assertTrue(prof["voice"])

    def test_save_and_load_roundtrip(self):
        self.assertTrue(self.V.save_profile(
            {"voice": "zh-CN-YunxiNeural", "pitch_base": 30,
             "rate_base": -10, "volume": 5, "notes": "偏软"}))
        prof = self.V.load_profile()
        self.assertEqual(prof["voice"], "zh-CN-YunxiNeural")
        self.assertEqual(prof["pitch_base"], 30)
        self.assertEqual(prof["rate_base"], -10)
        self.assertEqual(prof["volume"], 5)
        self.assertEqual(prof["notes"], "偏软")

    def test_broken_file_falls_back(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{ 这不是 json")
        prof = self.V.load_profile()
        self.assertEqual(prof["pitch_base"], 0, "坏文件应回落默认")

    def test_describe_shape(self):
        text = self.V.describe()
        self.assertIn("声线", text)
        self.assertIn("音高", text)


class TestEmotion(unittest.TestCase):
    """情绪 → 参数：五档、基线是平静、摩擦优先"""

    def setUp(self):
        from bot.speech import voice

        self.V = voice

    def test_all_emotions(self):
        for emo in ("平静", "开心", "撒娇", "难过", "生气"):
            p = self.V.emotion_params(emo)
            self.assertEqual(p["emotion"], emo)
            self.assertIn("voice", p)
            self.assertIn("rate", p)

    def test_unknown_falls_back(self):
        self.assertEqual(self.V.emotion_params("狂喜")["emotion"], "平静")

    def test_baseline_mood_is_calm(self):
        """基线 mood=0.10 不能判成难过"""
        self.assertEqual(self.V.emotion_from(0.10, 0, 0), "平静")

    def test_low_mood_sad(self):
        self.assertEqual(self.V.emotion_from(-0.2, 0, 0), "难过")

    def test_high_mood_happy(self):
        self.assertEqual(self.V.emotion_from(0.6, 0, 0), "开心")

    def test_friction_angry_wins(self):
        self.assertEqual(self.V.emotion_from(0.9, 0.8, 0.9), "生气")

    def test_close_is_sweet(self):
        self.assertEqual(self.V.emotion_from(0.1, 0, 0.8), "撒娇")

    def test_happy_beats_sweet(self):
        self.assertEqual(self.V.emotion_from(0.9, 0, 0.9), "开心")

    def test_params_add_profile_base(self):
        prof = {"voice": "v", "pitch_base": 10, "rate_base": 5,
                "volume": 2, "notes": ""}
        p = self.V.emotion_params("开心", prof)
        self.assertEqual(p["pitch"], 40, "10 + 30")
        self.assertEqual(p["rate"], 13, "5 + 8")
        self.assertEqual(p["volume"], 5, "2 + 3")


class TestVoiceCommand(unittest.TestCase):
    """!voice：查看 / 调参 / 试听 / 合成"""

    def setUp(self):
        import bot.commands  # noqa: F401
        from bot.cmd import registry
        from bot.speech import tts as T
        from bot.speech import voice

        self.cmd = registry.COMMANDS["voice"]
        self.V = voice
        self.T = T
        self.saved = {}
        self._orig = (voice.load_profile, voice.save_profile,
                      T.synth, T.available)
        self.V.load_profile = lambda persona=None: dict(
            {"voice": "zh-CN-XiaoxiaoNeural", "pitch_base": 0,
             "rate_base": 0, "volume": 0, "notes": ""}, **self.saved)
        self.V.save_profile = lambda data, persona=None: self.saved.update(
            {k: data[k] for k in data if k in ("voice", "pitch_base",
                                               "rate_base", "volume")}) or True

    def tearDown(self):
        (self.V.load_profile, self.V.save_profile,
         self.T.synth, self.T.available) = self._orig

    def _run(self, text):
        from bot.cmd.registry import CommandContext

        ctx = CommandContext(parts=[p for p in text.split() if p],
                             uid="1", ws=None, is_group=False, gid=0)
        return asyncio.run(self.cmd.handler(ctx))

    def test_show(self):
        out = self._run("!voice")
        self.assertIn("声线", out)

    def test_set_voice(self):
        out = self._run("!voice set zh-CN-YunxiNeural")
        self.assertIn("Yunxi", out)
        self.assertEqual(self.saved["voice"], "zh-CN-YunxiNeural")

    def test_pitch(self):
        out = self._run("!voice pitch 30")
        self.assertIn("+30", out)
        self.assertEqual(self.saved["pitch_base"], 30)

    def test_pitch_out_of_range(self):
        out = self._run("!voice pitch 200")
        self.assertIn("要在", out)
        self.assertNotIn("pitch_base", self.saved)

    def test_reset(self):
        self.saved["pitch_base"] = 30
        out = self._run("!voice reset")
        self.assertIn("默认", out)

    def test_note(self):
        out = self._run("!voice note 偏软一点")
        self.assertIn("备注", out)

    def test_text_still_sends_voice(self):
        """原有行为：!voice <文本> 合成并发送"""
        T = self.T
        sent = []
        T.available = lambda: True

        async def fake_synth(text, voice=None, rate=0, pitch=0, volume=0):
            sent.append({"text": text, "voice": voice, "rate": rate})
            return b"MP3"

        async def fake_send_voice(uid, mp3, ws):
            sent.append({"sent": mp3})

        T.synth = fake_synth
        import bot.chat.send as chat_send

        orig = chat_send.send_voice
        chat_send.send_voice = fake_send_voice
        try:
            out = self._run("!voice 今天有点累")
        finally:
            chat_send.send_voice = orig
        self.assertEqual(out, "", "发完语音不再追加文字")
        self.assertTrue(any(x.get("sent") == b"MP3" for x in sent))


if __name__ == "__main__":
    unittest.main()
