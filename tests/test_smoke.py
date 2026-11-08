# ===================== 冒烟测试 =====================
# v5-R0：给重构建立基线。
# 运行：python -m unittest discover -s tests -v
#
# 约定：
#   - 标了 @unittest.expectedFailure 的用例，记录的是「已知 bug 的当前行为」。
#     修好之后去掉装饰器，它就会变成守护用例。
#   - 本机缺 pymysql / jieba / aiohttp / PIL 时自动打桩；装了真依赖则不打桩。

import asyncio
import sys
import types
import unittest

# Windows 控制台默认 GBK，日志里有 emoji，统一成 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _stub_missing_deps():
    """只在依赖真的缺失时打桩，避免污染真实环境"""
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

    try:
        import jieba  # noqa: F401
    except ImportError:
        module("jieba", lcut=lambda s: list(s))

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        module("aiohttp")

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        module("PIL", Image=None)


_stub_missing_deps()

from botv.core import state as cfg             # noqa: E402  运行时状态（常量也在里面）
import botv.commands as commands               # noqa: E402
import botv.chat.reply as reply_mod            # noqa: E402
from botv.ai.parse import parse_ai_reply       # noqa: E402
from botv.cmd import registry                  # noqa: E402


class FakeWS:
    """假的 WebSocket，只记录发出去的内容"""

    def __init__(self):
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)

    def texts(self):
        """把发出去的 JSON 里的文本抽出来"""
        import json
        out = []
        for raw in self.sent:
            d = json.loads(raw)
            for seg in d["params"]["message"]:
                if seg.get("type") == "text":
                    out.append(seg["data"]["text"])
        return out


class TestParse(unittest.TestCase):
    """AI 回复解析"""

    def test_five_lines(self):
        ans = "你好\n（歪头）\n关键词搜索图片用：猫,狗\n事件摘要：测试 | 标签：a,b\n关键词提炼：a,b"
        dialog, action, img_kw, event, refined = parse_ai_reply(ans)
        self.assertEqual(dialog, "你好")
        self.assertEqual(action, "（歪头）")
        self.assertEqual(img_kw, ["猫", "狗"])
        self.assertEqual(event, "测试")
        self.assertEqual(refined, ["a", "b"])

    def test_single_line(self):
        dialog, action, img_kw, event, refined = parse_ai_reply("只有一句话")
        self.assertEqual(dialog, "只有一句话")
        self.assertEqual(action, "")
        self.assertEqual(img_kw, [])

    def test_none_action(self):
        _, action, _, _, _ = parse_ai_reply("嗯\n（无）")
        self.assertEqual(action, "")

    def test_empty_input(self):
        self.assertEqual(parse_ai_reply(None), ("嗯嗯", "", [], "", []))


class TestReplyAssembly(unittest.TestCase):
    """回复组装：当前行为快照"""

    def setUp(self):
        cfg.CODE_MODE = False
        # 图片搜索依赖数据库，测试里直接短路
        self._orig_get_best_image = reply_mod.get_best_image

        async def _no_image(*args, **kwargs):
            return None

        reply_mod.get_best_image = _no_image

    def tearDown(self):
        reply_mod.get_best_image = self._orig_get_best_image

    def _build(self, text):
        parts = asyncio.run(reply_mod.build_reply_message(text, "10001"))
        return [seg[0]["data"]["text"] for kind, seg in parts if kind == "text"]

    def test_first_two_lines_sent(self):
        texts = self._build("第一句\n（笑）")
        self.assertEqual(texts, ["第一句", "（笑）"])

    def test_multiline_dialog_keeps_all_lines(self):
        """F3：多行对话不再被吞，合成一条气泡"""
        texts = self._build("第一句\n第二句\n第三句")
        self.assertEqual(len(texts), 1)
        for s in ("第一句", "第二句", "第三句"):
            self.assertIn(s, texts[0])

    def test_no_action_sends_no_bubble(self):
        """F1：无动作时不该补一条「（无）」"""
        texts = self._build("只有对话")
        self.assertEqual(texts, ["只有对话"])

    def test_meta_lines_not_sent(self):
        """元数据按标记识别，不进对话"""
        texts = self._build("正文\n关键词搜索图片用：猫\n事件摘要：x\n关键词提炼：a")
        self.assertEqual(texts, ["正文"])

    def test_code_mode_single_message(self):
        """F3：代码模式整段发一条，代码块不被拆散"""
        cfg.CODE_MODE = True
        texts = self._build("答案开头\n```python\nprint(1)\n```\n答案结尾")
        self.assertEqual(len(texts), 1)
        self.assertIn("print(1)", texts[0])
        self.assertIn("答案结尾", texts[0])


class TestCommandRegistry(unittest.TestCase):
    """命令注册表与分发"""

    EXPECTED = {
        "acg", "apikeys", "clear", "clip", "code", "db", "diary", "event",
        "exit", "help", "img", "keywords", "log", "memory", "ping", "quit",
        "reload", "say", "sayg", "set", "status", "sticker", "task",
        "uptime", "usage",
    }

    def setUp(self):
        cfg.CODE_MODE = False

    def _run(self, text, uid=None):
        ws = FakeWS()
        uid = uid if uid is not None else str(cfg.MASTER_QQ)
        handled = asyncio.run(commands.handle_command(text, uid, ws, False, 0))
        return handled, ws

    def test_all_commands_registered(self):
        self.assertEqual(set(registry.COMMANDS), self.EXPECTED)

    def test_help(self):
        handled, ws = self._run("!help")
        self.assertTrue(handled)
        self.assertIn("可用命令", ws.texts()[0])

    def test_ping(self):
        handled, ws = self._run("!ping")
        self.assertTrue(handled)
        self.assertIn("Pong", ws.texts()[0])

    def test_status(self):
        handled, ws = self._run("!status")
        self.assertIn("状态概览", ws.texts()[0])

    def test_unknown_command(self):
        handled, ws = self._run("!nope")
        self.assertTrue(handled)
        self.assertIn("未知命令", ws.texts()[0])

    def test_non_master_ignored(self):
        handled, ws = self._run("!help", uid="123456")
        self.assertFalse(handled)
        self.assertEqual(ws.sent, [])

    def test_non_command_ignored(self):
        handled, ws = self._run("你好呀")
        self.assertFalse(handled)
        self.assertEqual(ws.sent, [])


class TestStructure(unittest.TestCase):
    """结构约定：迁移后这些东西必须还在原位"""

    def test_api_shim_reexports_same_objects(self):
        import botv.api as api
        import botv.ai.client as client
        self.assertIs(api.get_character_reply, client.get_character_reply)
        self.assertIs(api.call_deepseek, client.call_deepseek)

    def test_send_reexports_build_reply(self):
        import botv.send as send
        self.assertIs(send.build_reply_message, reply_mod.build_reply_message)

    def test_http_session_factory(self):
        from botv.core.http import create_http_session
        import requests
        session = create_http_session()
        self.assertIsInstance(session, requests.Session)
        session.close()


class TestFallback(unittest.TestCase):
    """F2：兜底文案不得入库、不得污染关键词"""

    def test_fallback_is_str(self):
        from botv.core.types import Fallback
        f = Fallback("哼")
        self.assertIsInstance(f, str)
        self.assertEqual(f, "哼")

    def test_get_character_reply_marks_fallback(self):
        import botv.ai.client as client
        import botv.memory as mem
        from botv.core.types import Fallback

        async def no_ds(*a, **k):
            return None

        async def fb_doubao(*a, **k):
            return Fallback("哼(扭头)")

        orig_ds, orig_db = client.call_deepseek, client.call_doubao
        orig_ev = mem.load_events_from_db
        client.call_deepseek, client.call_doubao = no_ds, fb_doubao
        mem.load_events_from_db = lambda *a, **k: []  # 测试环境不连库
        try:
            r = asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            client.call_deepseek, client.call_doubao = orig_ds, orig_db
            mem.load_events_from_db = orig_ev
        self.assertIsInstance(r, Fallback)

    def test_add_memory_skips_fallback(self):
        import botv.memory as mem
        from botv.core.types import Fallback

        calls = []
        orig = mem.add_user_memory_to_db
        orig_kw = mem.add_global_keywords_to_db
        mem.add_user_memory_to_db = lambda *a, **k: calls.append(a)
        mem.add_global_keywords_to_db = lambda *a, **k: None  # 测试环境不连库
        try:
            mem.add_target_memory("1", "hi", Fallback("哼"))
            mem.add_target_memory("1", "hi", "正常回复")
        finally:
            mem.add_user_memory_to_db = orig
            mem.add_global_keywords_to_db = orig_kw
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], "正常回复")


class TestImagePath(unittest.TestCase):
    """F4：图片路径解析不依赖当前工作目录"""

    def test_empty(self):
        from botv.utils import resolve_image_path
        self.assertIsNone(resolve_image_path(""))
        self.assertIsNone(resolve_image_path(None))

    def test_relative_resolved_from_project_root(self):
        import os
        from botv.utils import resolve_image_path
        p = resolve_image_path("README.md")  # 项目根下确定存在的文件
        self.assertIsNotNone(p)
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(os.path.exists(p))

    def test_missing_returns_none(self):
        from botv.utils import resolve_image_path
        self.assertIsNone(resolve_image_path("no/such/file.jpg"))

    def test_absolute_existing(self):
        import os
        from botv.utils import resolve_image_path
        p = resolve_image_path(os.path.abspath("README.md"))
        self.assertIsNotNone(p)


class TestOnlineNotice(unittest.TestCase):
    """F5：重连时上线通知不能重复刷"""

    def setUp(self):
        cfg.last_online_notice_ts = 0.0

    def tearDown(self):
        cfg.last_online_notice_ts = 0.0

    def test_first_call_claims(self):
        from botv.chat.handler import claim_online_notice
        self.assertTrue(claim_online_notice())

    def test_second_call_blocked(self):
        from botv.chat.handler import claim_online_notice
        self.assertTrue(claim_online_notice())
        self.assertFalse(claim_online_notice())

    def test_after_cooldown_allowed(self):
        from botv.chat.handler import claim_online_notice
        self.assertTrue(claim_online_notice())
        cfg.last_online_notice_ts -= 61  # 模拟 61 秒前
        self.assertTrue(claim_online_notice())


class TestTimePerception(unittest.TestCase):
    """F7：prompt 里必须带当前时间"""

    def setUp(self):
        cfg.CODE_MODE = False

    def test_now_text_format(self):
        from datetime import datetime
        from botv.ai.prompt import now_text
        from botv.config import CST
        s = now_text(datetime(2026, 11, 8, 23, 30, tzinfo=CST))
        self.assertIn("2026年11月8日", s)
        self.assertIn("23:30", s)
        self.assertIn("深夜", s)

    def test_morning_period(self):
        from datetime import datetime
        from botv.ai.prompt import now_text
        from botv.config import CST
        s = now_text(datetime(2026, 11, 9, 7, 15, tzinfo=CST))
        self.assertIn("早上", s)

    def test_prompt_contains_now(self):
        import botv.ai.client as client
        import botv.memory as mem

        captured = {}

        async def fake_ds(msgs, max_tokens=None, target_id=None):
            captured["sys"] = msgs[0]["content"]
            return "好"

        orig_ds, orig_ev = client.call_deepseek, mem.load_events_from_db
        client.call_deepseek = fake_ds
        mem.load_events_from_db = lambda *a, **k: []
        try:
            asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            client.call_deepseek = orig_ds
            mem.load_events_from_db = orig_ev

        self.assertIn("现在的时间", captured["sys"])
        self.assertNotIn("{now}", captured["sys"])
        self.assertRegex(captured["sys"], r"\d{4}年\d{1,2}月\d{1,2}日 周")


class TestOutbox(unittest.TestCase):
    """F6：断线期间的消息入队，重连后补发"""

    def setUp(self):
        cfg.pending_outbox.clear()

    def tearDown(self):
        cfg.pending_outbox.clear()

    def test_queue_when_disconnected(self):
        from botv.chat.send import send_private_msg
        ok = asyncio.run(send_private_msg(123, [{"type": "text", "data": {"text": "hi"}}], None))
        self.assertFalse(ok)
        self.assertEqual(len(cfg.pending_outbox), 1)

    def test_flush_after_reconnect(self):
        from botv.chat.send import send_private_msg, flush_outbox
        ws = FakeWS()
        asyncio.run(send_private_msg(123, [{"type": "text", "data": {"text": "a"}}], None))
        asyncio.run(send_private_msg(456, [{"type": "text", "data": {"text": "b"}}], None))
        sent = asyncio.run(flush_outbox(ws))
        self.assertEqual(sent, 2)
        self.assertEqual(len(cfg.pending_outbox), 0)
        self.assertEqual(len(ws.sent), 2)

    def test_flush_noop_when_empty(self):
        from botv.chat.send import flush_outbox
        self.assertEqual(asyncio.run(flush_outbox(FakeWS())), 0)


class TestHeartbeatWatchdog(unittest.TestCase):
    """F6：心跳连续失败要主动断开"""

    def test_closes_after_failures(self):
        from botv import heartbeat as hb

        class BadWS:
            closed = False

            def __init__(self):
                self.closed_count = 0

            async def ping(self):
                raise RuntimeError("dead")

            async def close(self):
                self.closed = True
                self.closed_count += 1

        ws = BadWS()
        orig = hb.HEARTBEAT_INTERVAL
        hb.HEARTBEAT_INTERVAL = 0.01
        try:
            async def run():
                task = asyncio.create_task(hb.heartbeat_monitor("T", ws))
                await asyncio.sleep(0.1)
                task.cancel()
            asyncio.run(run())
        finally:
            hb.HEARTBEAT_INTERVAL = orig
        self.assertTrue(ws.closed)
        self.assertGreaterEqual(ws.closed_count, 1)


class TestAntiAIStyle(unittest.TestCase):
    """v6-A23：反 AI 腔清单必须进 prompt"""

    def setUp(self):
        cfg.CODE_MODE = False

    def test_prompt_has_style_block(self):
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        self.assertIn("别像 AI", p)
        self.assertIn("总而言之", p)
        self.assertIn("我理解你的感受", p)

    def test_code_mode_has_hint(self):
        from botv.ai.prompt import get_system_prompt
        cfg.CODE_MODE = True
        try:
            p = get_system_prompt()
        finally:
            cfg.CODE_MODE = False
        self.assertIn("总而言之", p)


if __name__ == "__main__":
    unittest.main()
