# ===================== v19.3 语音/文字分段 =====================
import asyncio
import unittest

from tests.test_chat import _stub_missing_deps

_stub_missing_deps()

from bot.chat import segments


class TestSegments(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(segments.parse("你好"), [("text", "你好")])

    def test_pure_voice(self):
        self.assertEqual(segments.parse("【语音】今天好累【/语音】"),
                         [("voice", "今天好累")])

    def test_mixed_order(self):
        self.assertEqual(
            segments.parse("【文字】先说：【/文字】【语音】不去了。【/语音】"),
            [("text", "先说："), ("voice", "不去了。")])

    def test_unclosed_is_text_without_marker(self):
        self.assertEqual(segments.parse("【语音】没闭合"), [("text", "没闭合")])
        self.assertEqual(segments.strip_markers("【语音】没闭合"), "没闭合")

    def test_empty_voice_skipped(self):
        self.assertEqual(segments.parse("【语音】【/语音】你好"), [("text", "你好")])


class TestSendSegmented(unittest.TestCase):
    def test_voice_then_text_order_and_fallback(self):
        from bot.chat import send as S

        calls = []
        orig = (S.send_short_reply, S.send_voice, S.__dict__.get("tts_synth"))
        S.send_short_reply = lambda tid, text, ws, uid, is_group=False, kws=None: (
            calls.append(("text", text)) or _true())
        S.send_voice = lambda tid, mp3, ws, is_group=False: (
            calls.append(("voice", mp3)) or _true())
        try:
            from bot.speech import tts
            orig_synth = tts.synth
            tts.synth = lambda text, **kw: _bytes()
            try:
                asyncio.run(S.send_segmented_reply(
                    "1", "【语音】第一段【/语音】【文字】第二段【/文字】", None, "1"))
            finally:
                tts.synth = orig_synth
        finally:
            (S.send_short_reply, S.send_voice) = orig[0], orig[1]
        self.assertEqual([c[0] for c in calls], ["voice", "text"])


async def _true():
    return True


async def _bytes():
    return b"mp3"


if __name__ == "__main__":
    unittest.main()
