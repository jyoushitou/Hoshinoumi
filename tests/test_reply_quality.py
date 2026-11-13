"""v16.0.5 热修：重复回复 / 无关表情包 / 空语音"""

import unittest


class TestDuplicateReply(unittest.TestCase):
    def setUp(self):
        import bot.chat.send as S
        self.S = S
        S._recent_replies.clear()

    def tearDown(self):
        self.S._recent_replies.clear()

    def test_duplicate_blocked(self):
        self.assertFalse(self.S.is_duplicate_reply("1", "烦什么。"))
        self.assertTrue(self.S.is_duplicate_reply("1", "烦什么？"), "标点不同也算重复")

    def test_duplicate_expires(self):
        import time
        self.S.is_duplicate_reply("1", "烦什么。")
        old = time.time() + self.S.RECENT_REPLY_TTL + 1
        self.assertFalse(self.S.is_duplicate_reply("1", "烦什么。", now=old))

    def test_short_reply_not_blocked(self):
        self.S.is_duplicate_reply("1", "嗯")
        self.assertFalse(self.S.is_duplicate_reply("1", "嗯"), "太短的话不拦")

    def test_different_targets_independent(self):
        self.S.is_duplicate_reply("1", "烦什么。")
        self.assertFalse(self.S.is_duplicate_reply("2", "烦什么。"))

    def test_send_short_reply_skips_duplicate(self):
        import asyncio
        import bot.chat.send as S

        sent = []
        orig = S.send_private_msg

        async def fake_send(*a, **k):
            sent.append(a)

        from bot.core import metrics
        before = metrics.snapshot()[0].get("duplicate_reply", 0)
        S.send_private_msg = fake_send
        try:
            asyncio.run(S.send_short_reply("9", "烦什么。", None, "9"))
            asyncio.run(S.send_short_reply("9", "烦什么。", None, "9"))
        finally:
            S.send_private_msg = orig
        self.assertEqual(len(sent), 1, "第二次重复应被跳过")
        after = metrics.snapshot()[0].get("duplicate_reply", 0)
        self.assertEqual(after, before + 1, "重复回复应计入 duplicate_reply")


class TestVoiceWorthy(unittest.TestCase):
    def test_punctuation_only(self):
        import bot.chat.send as S
        self.assertFalse(S._voice_worthy("……"))
        self.assertFalse(S._voice_worthy("？？？"))
        self.assertFalse(S._voice_worthy(""))

    def test_normal_text(self):
        import bot.chat.send as S
        self.assertTrue(S._voice_worthy("今天好累啊"))


class TestStickerContext(unittest.TestCase):
    def test_no_ctx_returns_face(self):
        """没有上下文 → 退 QQ 表情，不随机甩存档图"""
        import bot.chat.send as S
        out = S.select_best_sticker("123", "")
        self.assertTrue(str(out).isdigit(), f"应该是表情 ID，实际 {out}")

    def test_archive_ignored_without_ctx(self):
        import bot.chat.send as S
        from bot.core import state as cfg
        cfg.USER_STICKER_ARCHIVE["999"] = ["deadbeef"]
        cfg.STICKER_DATA["deadbeef"] = {"path": "x"}
        out = S.select_best_sticker("999", "")
        self.assertTrue(str(out).isdigit())

    def test_signature_accepts_ctx(self):
        import inspect
        import bot.chat.send as S
        for fn in (S.send_sticker_private, S.send_sticker_group):
            params = inspect.signature(fn).parameters
            self.assertIn("ctx", params, f"{fn.__name__} 应接受 ctx")




class TestVoiceGateWired(unittest.TestCase):
    """v17.13：门槛要真接在发送路径上，不是只定义了个函数"""

    def test_maybe_send_voice_rejects_punctuation(self):
        import asyncio
        import bot.chat.send as S

        class Boom(Exception):
            pass

        called = []

        async def fake_synth(*a, **k):
            called.append(1)
            return b"MP3"

        orig = S.tts_synth
        S.tts_synth = fake_synth
        try:
            ok = asyncio.run(S.maybe_send_voice("……", "1", None))
        finally:
            S.tts_synth = orig
        self.assertFalse(ok, "纯标点不该合成")
        self.assertEqual(called, [], "连 TTS 都不该调")

    def test_sticker_ctx_from_handler(self):
        """handler 贴图时应把用户原话传下去"""
        import inspect
        import bot.chat.handler as H

        src = inspect.getsource(H)
        self.assertIn("send_sticker_private(uid, ws, uid, text)", src)
        self.assertIn("send_sticker_group(gid, ws, uid, text)", src)


if __name__ == "__main__":
    unittest.main()
