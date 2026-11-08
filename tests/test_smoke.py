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

    def test_multiline_dialog_one_bubble_per_line(self):
        """v6-A12：一行一个气泡，行数由模型决定"""
        texts = self._build("第一句\n第二句\n第三句")
        self.assertEqual(texts, ["第一句", "第二句", "第三句"])

    def test_too_many_lines_merged(self):
        """异常保护：只有超过 10 行才合并尾部"""
        text = "\n".join(f"第{i}行" for i in range(1, 16))
        texts = self._build(text)
        self.assertEqual(len(texts), 10)
        self.assertIn("第15行", texts[-1])

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
        "uptime", "usage", "profile",
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
        import botv.memory.context as mem
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
        import botv.memory.context as mem
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
        import botv.memory.context as mem

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


class TestFewShot(unittest.TestCase):
    """v6-A22：示例对话要进 prompt，且不带 AI 腔"""

    def setUp(self):
        cfg.CODE_MODE = False

    def test_prompt_has_examples(self):
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        self.assertIn("她说话的样子", p)
        self.assertIn("主人：", p)
        self.assertIn("奈绪：", p)

    def test_examples_show_optional_action(self):
        """示例里要有一条没有动作的，告诉模型动作可省"""
        from botv.ai.prompt import get_system_prompt
        p = get_system_prompt()
        block = p.split("【她说话的样子】")[1].split("回复必须")[0]
        lines = [l for l in block.split("\n") if l.startswith("奈绪：")]
        self.assertTrue(any("（" not in l for l in lines), "至少要有一条没动作的示例")


class TestBubbleDelay(unittest.TestCase):
    """v6-A12：气泡间隔随机，不是固定值"""

    def test_range(self):
        from botv.chat.send import bubble_delay, BUBBLE_DELAY_RANGE
        lo, hi = BUBBLE_DELAY_RANGE
        samples = [bubble_delay() for _ in range(200)]
        self.assertTrue(all(lo <= d <= hi for d in samples))
        self.assertGreater(len(set(samples)), 1, "应该是随机的")


class TestAtDetection(unittest.TestCase):
    """v6-E29：@ 判断"""

    def test_at_me(self):
        from botv.chat.inbound import is_at_me
        msg = [{"type": "text", "data": {"text": "hi"}},
               {"type": "at", "data": {"qq": "12345"}}]
        self.assertTrue(is_at_me(msg, 12345))
        self.assertFalse(is_at_me(msg, 999))
        self.assertFalse(is_at_me("plain text", 12345))

    def test_no_self_qq(self):
        from botv.chat.inbound import is_at_me
        msg = [{"type": "at", "data": {"qq": "12345"}}]
        self.assertFalse(is_at_me(msg, 0))


class _FakeRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


class TestGroupGate(unittest.TestCase):
    """v6-E29：群聊节奏闸门"""

    def setUp(self):
        cfg.group_last_reply_ts.clear()
        cfg.group_msg_window.clear()

    def tearDown(self):
        cfg.group_last_reply_ts.clear()
        cfg.group_msg_window.clear()

    def test_addressed_passes(self):
        from botv.chat.handler import should_answer_group
        ok, why = should_answer_group(111, True)
        self.assertTrue(ok)
        self.assertEqual(why, "被@")

    def test_cooldown_blocks_unaddressed(self):
        from botv.chat.handler import should_answer_group, note_group_reply
        note_group_reply(111)
        ok, why = should_answer_group(111, False)
        self.assertFalse(ok)
        self.assertIn("冷却", why)

    def test_window_full_blocks_even_addressed(self):
        from botv.chat import handler as h
        for _ in range(h.GROUP_WINDOW_MAX):
            h.note_group_reply(222)
        ok, why = h.should_answer_group(222, True)
        self.assertFalse(ok)
        self.assertIn("60秒内", why)

    def test_probability_gate(self):
        from botv.chat import handler as h
        orig = h.random
        try:
            h.random = _FakeRandom(0.0)  # 一定命中
            ok, why = h.should_answer_group(333, False)
            self.assertTrue(ok)
            self.assertEqual(why, "随机接话")

            h.cfg.group_last_reply_ts.clear()
            h.random = _FakeRandom(0.99)  # 一定不中
            ok, why = h.should_answer_group(333, False)
            self.assertFalse(ok)
            self.assertIn("概率", why)
        finally:
            h.random = orig


class TestReplyTiming(unittest.TestCase):
    """v6-A1：延迟按时段浮动，且偏短"""

    class _R:
        def __init__(self, v):
            self.v = v

        def random(self):
            return self.v

    def test_bands(self):
        from datetime import datetime
        from botv.chat.timing import delay_range
        from botv.config import CST
        self.assertEqual(delay_range(datetime(2026, 1, 1, 2, tzinfo=CST)), (20, 180))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 10, tzinfo=CST)), (5, 30))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 20, tzinfo=CST)), (8, 60))
        self.assertEqual(delay_range(datetime(2026, 1, 1, 23, 30, tzinfo=CST)), (20, 120))

    def test_within_range(self):
        from datetime import datetime
        from botv.chat.timing import reply_delay
        from botv.config import CST
        now = datetime(2026, 1, 1, 10, tzinfo=CST)
        for v in (0.0, 0.5, 0.999):
            d = reply_delay(now, self._R(v))
            self.assertGreaterEqual(d, 5)
            self.assertLessEqual(d, 30)

    def test_biased_short(self):
        from datetime import datetime
        from botv.chat.timing import reply_delay
        from botv.config import CST
        now = datetime(2026, 1, 1, 10, tzinfo=CST)
        vals = [reply_delay(now, self._R(i / 100)) for i in range(100)]
        mean = sum(vals) / len(vals)
        self.assertLess(mean, 17.5, f"应偏短，实际均值 {mean:.1f}")


class TestConcurrency(unittest.TestCase):
    """v6-E26：按对象分片锁 + 模型调用上限"""

    def setUp(self):
        cfg.target_locks.clear()

    def tearDown(self):
        cfg.target_locks.clear()

    def test_same_target_serialized(self):
        from botv.core.locks import get_target_lock
        st = {"active": 0, "peak": 0}

        async def run():
            async def worker():
                async with get_target_lock("x"):
                    st["active"] += 1
                    st["peak"] = max(st["peak"], st["active"])
                    await asyncio.sleep(0.01)
                    st["active"] -= 1
            await asyncio.gather(worker(), worker(), worker())

        asyncio.run(run())
        self.assertEqual(st["peak"], 1, "同一个人必须串行")

    def test_different_targets_parallel(self):
        from botv.core.locks import get_target_lock
        st = {"active": 0, "peak": 0}

        async def run():
            async def worker(tid):
                async with get_target_lock(tid):
                    st["active"] += 1
                    st["peak"] = max(st["peak"], st["active"])
                    await asyncio.sleep(0.02)
                    st["active"] -= 1
            await asyncio.gather(worker("a"), worker("b"), worker("c"))

        asyncio.run(run())
        self.assertEqual(st["peak"], 3, "三个人应该能并行")

    def test_cleanup_idle_locks(self):
        from botv.core import locks
        locks.get_target_lock("old")
        locks._last_used["old"] -= 700
        removed = locks.cleanup_idle_locks()
        self.assertGreaterEqual(removed, 1)
        self.assertNotIn("old", cfg.target_locks)

    def test_model_semaphore_limit(self):
        from botv.core import locks
        locks._model_sem = None  # 每个用例用新的信号量，避免跨事件循环
        st = {"active": 0, "peak": 0}

        async def run():
            sem = locks.model_semaphore()

            async def call():
                async with sem:
                    st["active"] += 1
                    st["peak"] = max(st["peak"], st["active"])
                    await asyncio.sleep(0.01)
                    st["active"] -= 1
            await asyncio.gather(*[call() for _ in range(12)])

        asyncio.run(run())
        self.assertEqual(st["peak"], locks.MAX_CONCURRENT_MODEL_CALLS)


class TestTone(unittest.TestCase):
    """v6-A20：按时段给语气提示"""

    def test_bands(self):
        from datetime import datetime
        from botv.chat.timing import tone_hint
        from botv.config import CST
        self.assertIn("困", tone_hint(datetime(2026, 1, 1, 2, tzinfo=CST)))
        self.assertIn("刚醒", tone_hint(datetime(2026, 1, 1, 7, tzinfo=CST)))
        self.assertIn("精神", tone_hint(datetime(2026, 1, 1, 12, tzinfo=CST)))
        self.assertIn("放松", tone_hint(datetime(2026, 1, 1, 20, tzinfo=CST)))

    def test_prompt_has_tone(self):
        import botv.ai.client as client
        import botv.memory.context as mem
        from botv.core import locks
        captured = {}

        async def fake_ds(msgs, max_tokens=None, target_id=None):
            captured["sys"] = msgs[0]["content"]
            return "好"

        orig_ds, orig_ev = client.call_deepseek, mem.load_events_from_db
        client.call_deepseek = fake_ds
        mem.load_events_from_db = lambda *a, **k: []
        locks._model_sem = None
        try:
            asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            client.call_deepseek = orig_ds
            mem.load_events_from_db = orig_ev
        self.assertIn("你现在的状态", captured["sys"])
        self.assertNotIn("{tone}", captured["sys"])


class TestDedupeKey(unittest.TestCase):
    """v7-B14：记忆去重指纹"""

    def setUp(self):
        pass

    def test_punctuation_and_space_ignored(self):
        from botv.infra import dedupe as m
        a = m.dedupe_key("1", "event", "主人 明天要答辩！")
        b = m.dedupe_key("1", "event", "主人明天要答辩")
        self.assertEqual(a, b)

    def test_target_matters(self):
        from botv.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "同一句话"),
            m.dedupe_key("2", "event", "同一句话"),
        )

    def test_kind_matters(self):
        from botv.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "同一句话"),
            m.dedupe_key("1", "life", "同一句话"),
        )

    def test_different_text_differs(self):
        from botv.infra import dedupe as m
        self.assertNotEqual(
            m.dedupe_key("1", "event", "今天加班"),
            m.dedupe_key("1", "event", "今天加班到十点"),
        )


class _FakeCursor:
    """够用的假游标：记录执行过哪些语句"""

    def __init__(self, first_row=None):
        self.first_row = first_row
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((" ".join(str(sql).split()), params))

    def fetchone(self):
        return self.first_row

    def fetchall(self):
        return [self.first_row] if self.first_row else []

    @property
    def connection(self):
        return self

    def commit(self):
        pass

    def verbs(self):
        return [s[0].split()[0].upper() for s in self.statements]


class TestMemoryWriteDedupe(unittest.TestCase):
    """v7-B15：7 天内同键只累加，不新增"""

    def _run(self, existing):
        import botv.infra.repo_memory as rm
        cur = _FakeCursor(existing)
        orig = rm.get_cursor
        rm.get_cursor = lambda: cur
        try:
            rm.add_event_to_db("1", "今天加班", kind="event")
        finally:
            rm.get_cursor = orig
        return cur

    def test_hit_only_updates(self):
        cur = self._run({"id": 7})
        self.assertIn("UPDATE", cur.verbs())
        self.assertNotIn("INSERT", cur.verbs())

    def test_miss_inserts(self):
        cur = self._run(None)
        self.assertIn("INSERT", cur.verbs())
        self.assertIn("DELETE", cur.verbs())  # 插入后按 kind 裁剪

    def test_empty_summary_skipped(self):
        import botv.infra.repo_memory as rm
        cur = _FakeCursor(None)
        orig = rm.get_cursor
        rm.get_cursor = lambda: cur
        try:
            rm.add_event_to_db("1", "")
        finally:
            rm.get_cursor = orig
        self.assertEqual(cur.statements, [])


class TestProfile(unittest.TestCase):
    """v7-B9：画像解析与写入"""

    def test_get_profile_parses(self):
        import botv.infra.repo_profile as rp
        cur = _FakeCursor()
        cur.fetchall = lambda: [{"event_summary": "昵称：小奈"},
                                {"event_summary": "喜好：甜"},
                                {"event_summary": "没有冒号的坏数据"}]
        orig = rp.get_cursor
        rp.get_cursor = lambda: cur
        try:
            p = rp.get_profile("1")
        finally:
            rp.get_cursor = orig
        self.assertEqual(p, {"昵称": "小奈", "喜好": "甜"})

    def test_build_text(self):
        import botv.infra.repo_profile as rp
        orig = rp.get_profile
        rp.get_profile = lambda tid: {"昵称": "小奈", "禁忌": "别熬夜"}
        try:
            s = rp.build_profile_text("1")
        finally:
            rp.get_profile = orig
        self.assertIn("昵称=小奈", s)
        self.assertIn("禁忌=别熬夜", s)

    def test_empty_profile(self):
        import botv.infra.repo_profile as rp
        orig = rp.get_profile
        rp.get_profile = lambda tid: {}
        try:
            self.assertEqual(rp.build_profile_text("1"), "无")
        finally:
            rp.get_profile = orig

    def test_set_profile_is_delete_then_insert(self):
        import botv.infra.repo_profile as rp
        cur = _FakeCursor()
        orig = rp.get_cursor
        rp.get_cursor = lambda: cur
        try:
            ok = rp.set_profile("1", "昵称", "小奈")
        finally:
            rp.get_cursor = orig
        self.assertTrue(ok)
        self.assertEqual(cur.verbs()[:2], ["DELETE", "INSERT"])

    def test_set_profile_rejects_empty(self):
        import botv.infra.repo_profile as rp
        self.assertFalse(rp.set_profile("1", "", "x"))
        self.assertFalse(rp.set_profile("1", "昵称", "   "))


class TestSingleInstance(unittest.TestCase):
    """v7-E32：单实例锁"""

    def setUp(self):
        import os
        # 放在仓库目录里：系统临时目录在沙箱下不可写
        root = os.path.dirname(os.path.dirname(__file__))
        self.path = os.path.join(root, f".test-lock-{os.getpid()}")

    def tearDown(self):
        import os
        from botv.core import single_instance as si
        si.release()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_second_acquire_fails_then_release_works(self):
        from botv.core import single_instance as si
        self.assertTrue(si.acquire(self.path))
        self.assertFalse(si.acquire(self.path), "同一文件第二次必须拿不到")
        si.release()
        self.assertTrue(si.acquire(self.path), "释放后应该能重新拿到")

    def test_holder_pid_written(self):
        import os
        from botv.core import single_instance as si
        self.assertTrue(si.acquire(self.path))
        self.assertEqual(si.holder_pid(self.path), str(os.getpid()))


class TestBackupSqlLiteral(unittest.TestCase):
    """v7 备份脚本：SQL 字面量转义"""

    def setUp(self):
        import os as _os
        import sys as _sys
        scripts = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "scripts")
        if scripts not in _sys.path:
            _sys.path.insert(0, scripts)

    def test_values(self):
        import backup_table as b
        self.assertEqual(b.sql_literal(None), "NULL")
        self.assertEqual(b.sql_literal(3), "3")
        self.assertEqual(b.sql_literal(1.5), "1.5")

    def test_quote_escaped(self):
        import backup_table as b
        s = b.sql_literal("it's ok")
        self.assertTrue(s.startswith("'") and s.endswith("'"))
        self.assertIn("\\'", s)

    def test_bytes_hex(self):
        import backup_table as b
        self.assertEqual(b.sql_literal(b"\x01\x02"), "X'0102'")

    def test_datetime_and_date(self):
        from datetime import date, datetime
        import backup_table as b
        self.assertEqual(b.sql_literal(date(2026, 11, 8)), "'2026-11-08'")
        self.assertIn("2026-11-08 21:30", b.sql_literal(datetime(2026, 11, 8, 21, 30)))


class TestRetrieval(unittest.TestCase):
    """v8-B11/B17：BM25 + 关键词 + RRF"""

    MEMS = [
        {"summary": "defense tomorrow at school", "tags": "school", "importance": 4, "hit_count": 0},
        {"summary": "overtime until ten tonight", "tags": "work", "importance": 3, "hit_count": 2},
        {"summary": "cat broke a cup", "tags": "life", "importance": 2, "hit_count": 0},
    ]

    @staticmethod
    def tok(s):
        return [w for w in str(s).lower().split() if len(w) > 1]

    def test_hit_first(self):
        from botv.memory.retrieval import retrieve
        r = retrieve("defense", self.MEMS, top_k=2, tokenizer=self.tok)
        self.assertTrue(r)
        self.assertIn("defense", r[0][0]["summary"])

    def test_no_match_returns_empty(self):
        from botv.memory.retrieval import retrieve
        self.assertEqual(retrieve("quantum", self.MEMS, top_k=2, tokenizer=self.tok), [])

    def test_bm25_orders_correctly(self):
        from botv.memory.retrieval import BM25
        bm = BM25([m["summary"] for m in self.MEMS], tokenizer=self.tok)
        self.assertGreater(bm.score(["overtime"], 1), bm.score(["overtime"], 0))

    def test_rrf_prefers_common_head(self):
        from botv.memory.retrieval import rrf
        fused = rrf([[0, 1, 2], [2, 0, 1]])
        self.assertEqual(fused[0][0], 0)


class TestRecallMemories(unittest.TestCase):
    """v8-B11：检索接入上下文，命中优先、未命中兜底"""

    def test_uses_retrieval_when_hit(self):
        import botv.memory.context as ctx
        cands = [{"summary": "主人要答辩"}, {"summary": "加班"}]
        orig_l, orig_r = ctx.load_memories_for_search, ctx.retrieve
        ctx.load_memories_for_search = lambda tid, limit=300: cands
        ctx.retrieve = lambda q, ms, top_k=5: [(ms[0], 0.9)]
        try:
            s = ctx._recall_memories("1", "答辩")
        finally:
            ctx.load_memories_for_search, ctx.retrieve = orig_l, orig_r
        self.assertIn("答辩", s)
        self.assertNotIn("加班", s)

    def test_falls_back_when_no_hit(self):
        import botv.memory.context as ctx
        orig_l, orig_r, orig_e = ctx.load_memories_for_search, ctx.retrieve, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: [{"summary": "x"}]
        ctx.retrieve = lambda q, ms, top_k=5: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: [("最近的旧事", "")]
        try:
            s = ctx._recall_memories("1", "无关的查询")
        finally:
            ctx.load_memories_for_search, ctx.retrieve, ctx.load_events_from_db = orig_l, orig_r, orig_e
        self.assertIn("最近的旧事", s)

    def test_db_error_returns_placeholder(self):
        import botv.memory.context as ctx
        orig_l = ctx.load_memories_for_search
        def boom(tid, limit=300):
            raise RuntimeError("db down")
        ctx.load_memories_for_search = boom
        orig_e = ctx.load_events_from_db
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            self.assertEqual(ctx._recall_memories("1", "任何"), "无")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e


class TestBudget(unittest.TestCase):
    """v8-B13：分层预算"""

    def test_trim(self):
        from botv.memory.inject import trim
        self.assertEqual(trim("abc", 10), "abc")
        self.assertEqual(len(trim("x" * 100, 10)), 10)
        self.assertTrue(trim("x" * 100, 10).endswith("…"))

    def test_cap_lines_keeps_recent(self):
        from botv.memory.inject import cap_lines
        lines = [f"第{i}轮" for i in range(1, 21)]
        text, used = cap_lines(lines, 30)
        self.assertLessEqual(used, 30)
        self.assertIn("第20轮", text)
        self.assertNotIn("第1轮", text)

    def test_cap_lines_all_fit(self):
        from botv.memory.inject import cap_lines
        text, used = cap_lines(["a", "b"], 100)
        self.assertEqual(text, "a\nb")

    def test_report_flag(self):
        from botv.memory.inject import report
        self.assertIn("✅", report(a="x" * 10))

    def test_context_trims_dialogue(self):
        from collections import deque
        import botv.memory.context as ctx
        from botv.memory.inject import BUDGET
        cfg.user_memory_pool["9"] = deque([("长" * 200, "回" * 200)] * 10, maxlen=15)
        orig_l, orig_e = ctx.load_memories_for_search, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            _kw, dia, _ev = ctx.build_memory_context("9", None, query="hi")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e
            cfg.user_memory_pool.pop("9", None)
        self.assertEqual(dia.count("用户:"), 1, "10 轮长对话应被预算砍到 1 轮")


class TestTimeline(unittest.TestCase):
    """v8-B16：时间线格式"""

    def test_format(self):
        from datetime import date
        from botv.memory.timeline import format_timeline
        rows = [{"day": date(2026, 11, 7), "summary": "答辩"},
                {"day": date(2026, 11, 6), "summary": "加班"}]
        self.assertEqual(format_timeline(rows), "11-07 答辩\n11-06 加班")

    def test_empty(self):
        from botv.memory.timeline import format_timeline
        self.assertEqual(format_timeline([]), "无")

    def test_skip_empty_summary(self):
        from botv.memory.timeline import format_timeline
        rows = [{"day": None, "summary": ""}, {"day": "2026-11-05", "summary": "开会"}]
        s = format_timeline(rows)
        self.assertIn("11-05 开会", s)
        self.assertNotIn("??-??", s)

    def test_trimmed_to_budget(self):
        from botv.memory.timeline import format_timeline
        rows = [{"day": "2026-11-05", "summary": "很长的记忆" * 50}]
        self.assertLessEqual(len(format_timeline(rows)), 200)


class TestTimeoutTiers(unittest.TestCase):
    """v8-E28：超时分级"""

    def test_chat_vs_long(self):
        from botv.ai.client import _timeout_for
        from botv.core.constants import CHAT_TIMEOUT, LONG_TIMEOUT
        self.assertEqual(_timeout_for(200), CHAT_TIMEOUT)
        self.assertEqual(_timeout_for(1500), LONG_TIMEOUT)
        self.assertEqual(_timeout_for(None), CHAT_TIMEOUT)


class TestSessionReuse(unittest.TestCase):
    """v8-E27：线程本地会话复用"""

    def test_same_thread_same_session(self):
        from botv.core.http import get_http_session
        a = get_http_session()
        b = get_http_session()
        self.assertIs(a, b)

    def test_different_thread_different_session(self):
        import threading
        from botv.core.http import get_http_session
        main_session = get_http_session()
        box = {}

        def worker():
            box["s"] = get_http_session()

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        self.assertIsNot(box["s"], main_session)


class TestKeywordScoping(unittest.TestCase):
    """v8-B12：关键词按对象隔离"""

    def setUp(self):
        cfg.global_keyword_set = set()
        cfg.target_keyword_sets = {}

    def tearDown(self):
        cfg.global_keyword_set = set()
        cfg.target_keyword_sets = {}
        cfg.user_memory_pool.pop("A", None)

    def test_context_uses_own_words(self):
        import botv.memory.context as ctx
        cfg.global_keyword_set = {"公共词"}
        cfg.target_keyword_sets = {"A": {"甲的词"}, "B": {"乙的词"}}
        orig_l, orig_e = ctx.load_memories_for_search, ctx.load_events_from_db
        ctx.load_memories_for_search = lambda tid, limit=300: []
        ctx.load_events_from_db = lambda tid, tag_keywords=None, limit=3: []
        try:
            kw_a, _d, _e = ctx.build_memory_context("A", None, query="x")
            kw_b, _d, _e = ctx.build_memory_context("B", None, query="x")
        finally:
            ctx.load_memories_for_search, ctx.load_events_from_db = orig_l, orig_e
        self.assertIn("甲的词", kw_a)
        self.assertNotIn("乙的词", kw_a)
        self.assertIn("公共词", kw_a)
        self.assertIn("乙的词", kw_b)

    def test_write_goes_to_target(self):
        import botv.memory.context as ctx
        calls = []
        orig_kw, orig_u = ctx.add_global_keywords_to_db, ctx.add_user_memory_to_db
        ctx.add_global_keywords_to_db = lambda kws, tid="": calls.append((tid, list(kws)))
        ctx.add_user_memory_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("A", "hi", "回复", refined_keywords=["词1"])
        finally:
            ctx.add_global_keywords_to_db, ctx.add_user_memory_to_db = orig_kw, orig_u
        self.assertEqual(calls[0][0], "A")
        self.assertEqual(calls[0][1], ["词1"])


class TestReferer(unittest.TestCase):
    """v8-FIX：防盗链 Referer 跟图片域名走"""

    def test_own_domain(self):
        from botv.utils import referer_for
        self.assertEqual(referer_for("https://p6.itc.cn/q_70/a.jpg"), "https://p6.itc.cn/")
        self.assertEqual(referer_for("http://file.alapi.cn/image/x.jpg"), "http://file.alapi.cn/")

    def test_fallback(self):
        from botv.utils import referer_for
        self.assertEqual(referer_for(""), "https://www.google.com/")
        self.assertEqual(referer_for("not-a-url"), "https://www.google.com/")


class TestImageTagsBackfill(unittest.TestCase):
    """v8-CLIPCUT：用 AI 关键词回写图片标签"""

    def test_merge_and_dedup(self):
        import botv.image.store as store
        cur = _FakeCursor({"tags": "用户发图,猫"})
        orig = store.get_cursor
        store.get_cursor = lambda: cur
        try:
            n = store.update_image_tags(["abc"], ["猫", "可爱"])
        finally:
            store.get_cursor = orig
        self.assertEqual(n, 1)
        upd = [s for s in cur.statements if s[0].startswith("UPDATE")]
        self.assertEqual(upd[0][1][0], "用户发图,猫,可爱")

    def test_empty_keywords_noop(self):
        import botv.image.store as store
        self.assertEqual(store.update_image_tags(["abc"], []), 0)


if __name__ == "__main__":
    unittest.main()
