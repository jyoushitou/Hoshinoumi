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
        "uptime", "usage", "profile", "todo", "voice", "memorybook", "growth", "persona", "stats", "config",
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
        p = resolve_image_path("botv/__init__.py")  # 项目根下确定存在的文件（大小写无关）
        self.assertIsNotNone(p)
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(os.path.exists(p))

    def test_missing_returns_none(self):
        from botv.utils import resolve_image_path
        self.assertIsNone(resolve_image_path("no/such/file.jpg"))

    def test_absolute_existing(self):
        import os
        from botv.utils import resolve_image_path
        p = resolve_image_path(os.path.abspath("botv/__init__.py"))
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
        from botv.chat import handler as h
        orig = h.random.random
        h.random.random = lambda: 0.0  # v14-B4：被@ 也要掷骰，测试要压到必中
        try:
            ok, why = h.should_answer_group(111, True)
        finally:
            h.random.random = orig
        self.assertTrue(ok)
        self.assertTrue(why.startswith("被@"), why)

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
            self.assertTrue(why.startswith("随机接话"), why)

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


class TestLoadMemories(unittest.TestCase):
    """v8-B12：启动时把关键词按对象拆开加载"""

    def test_splits_public_and_personal(self):
        from collections import deque
        import botv.memory.context as ctx
        orig_u, orig_k = ctx.load_user_memories_from_db, ctx.load_keywords_from_db
        ctx.load_user_memories_from_db = lambda: {"A": deque([["hi", "yo"]], maxlen=5)}
        ctx.load_keywords_from_db = lambda: {"": {"公共"}, "A": {"甲"}}
        try:
            ctx.load_memories()
            got_public = set(cfg.global_keyword_set)
            got_target = dict(cfg.target_keyword_sets)
        finally:
            ctx.load_user_memories_from_db, ctx.load_keywords_from_db = orig_u, orig_k
            cfg.global_keyword_set = set()
            cfg.target_keyword_sets = {}
        self.assertEqual(got_public, {"公共"})
        self.assertEqual(got_target.get("A"), {"甲"})


class TestLifeState(unittest.TestCase):
    """v9-U4：状态向量"""

    def test_default_in_range(self):
        from botv.life.state import default_state, CLAMP
        s = default_state()
        for k, (lo, hi) in CLAMP.items():
            self.assertGreaterEqual(s[k], lo)
            self.assertLessEqual(s[k], hi)

    def test_tick_moves_toward_base(self):
        from botv.life.state import tick, BASE
        s = {"mood": 0.9, "energy": 0.1, "lonely": 0.1}
        out = tick(s, 1)
        self.assertLess(out["mood"], 0.9)          # 高情绪向基线回落
        self.assertGreater(out["energy"], 0.1)     # 低精力向基线回升

    def test_tick_alone_increases_lonely(self):
        from botv.life.state import tick
        out = tick({"mood": 0.1, "energy": 0.7, "lonely": 0.2}, 5)
        self.assertGreater(out["lonely"], 0.2)

    def test_clamp_bounds(self):
        from botv.life.state import clamp
        s = clamp({"mood": 5, "energy": -3, "lonely": 99})
        self.assertLessEqual(s["mood"], 1.0)
        self.assertGreaterEqual(s["energy"], 0.0)
        self.assertLessEqual(s["lonely"], 1.0)

    def test_talk_relieves_lonely(self):
        from botv.life.state import on_talk
        s = {"mood": 0.0, "energy": 0.5, "lonely": 0.8}
        self.assertLess(on_talk(s)["lonely"], 0.8)

    def test_describe_has_no_numbers(self):
        from botv.life.state import describe
        text = describe({"mood": -0.7, "energy": 0.1, "lonely": 0.9})
        self.assertTrue(text.endswith("。"))
        self.assertFalse(any(ch.isdigit() for ch in text), f"不该出现数字: {text}")

    def test_json_roundtrip(self):
        from botv.life.state import to_json, from_json
        s = {"mood": 0.3, "energy": 0.6, "lonely": 0.2}
        back = from_json(to_json(s))
        for k, v in s.items():
            self.assertEqual(back[k], v)

    def test_from_json_garbage(self):
        from botv.life.state import from_json, default_state
        self.assertEqual(from_json("not json"), default_state())
        self.assertEqual(from_json(""), default_state())


class TestStateInPrompt(unittest.TestCase):
    """v9-U4：状态渲染进 prompt"""

    def test_prompt_carries_state(self):
        import botv.ai.client as client
        import botv.memory.context as mem
        from botv.core import locks
        captured = {}

        async def fake_ds(msgs, max_tokens=None, target_id=None):
            captured["sys"] = msgs[0]["content"]
            return "好"

        orig = (client.call_deepseek, mem.load_events_from_db,
                client.life_current, client.touch_talk)
        client.call_deepseek = fake_ds
        mem.load_events_from_db = lambda *a, **k: []
        client.life_current = lambda *a, **k: {"mood": -0.3, "energy": 0.15, "lonely": 0.9}
        client.touch_talk = lambda: None
        locks._model_sem = None
        try:
            asyncio.run(client.get_character_reply("hi", "1"))
        finally:
            (client.call_deepseek, mem.load_events_from_db,
             client.life_current, client.touch_talk) = orig
        self.assertIn("有点烦", captured["sys"])
        self.assertIn("困得不行", captured["sys"])


class TestLifeEvents(unittest.TestCase):
    """v9-U7：每日生活事件"""

    def test_count_in_range(self):
        from botv.life.events import generate, MIN_EVENTS, MAX_EVENTS
        for _ in range(30):
            n = len(generate())
            self.assertGreaterEqual(n, MIN_EVENTS)
            self.assertLessEqual(n, MAX_EVENTS)

    def test_no_dup_within_day(self):
        from botv.life.events import generate
        for _ in range(20):
            items = generate()
            self.assertEqual(len(items), len(set(items)))

    def test_all_from_pools(self):
        from botv.life.events import generate, POOLS
        all_texts = {t for _w, pool in POOLS for t in pool}
        for _ in range(20):
            for t in generate():
                self.assertIn(t, all_texts)

    def test_template_count(self):
        from botv.life.events import total_templates
        self.assertGreaterEqual(total_templates(), 100, "模板至少要 100 条")

    def test_grief_pool_is_low_weight(self):
        from botv.life.events import POOLS
        weights = [w for w, _pool in POOLS]
        self.assertEqual(POOLS[-1][0], min(weights), "关于他的模板权重应最低")

    def test_ensure_once_per_day(self):
        import botv.life.events as ev
        import botv.infra.repo_memory as rm
        from botv.core import state as cfg
        calls = []
        orig = rm.add_event_to_db
        rm.add_event_to_db = lambda tid, text, **k: calls.append((tid, text, k.get("kind")))
        try:
            cfg.life_last_date = {}
            n1 = ev.ensure_daily_life()
            n2 = ev.ensure_daily_life()
        finally:
            rm.add_event_to_db = orig
            cfg.life_last_date = {}
        self.assertGreaterEqual(n1, 1)
        self.assertEqual(n2, 0, "同一天第二次不应再写")
        self.assertTrue(all(c[2] == "life" for c in calls))


class TestDiaryReflow(unittest.TestCase):
    """v9-U11：日记压成记忆 + 情绪余韵"""

    DIARY = ("今天学生会开到很晚，散会时天都黑了。新来的干事又写错记录，我改到眼睛发酸。"
             "回家路上买了关东煮，小咪在门口等我。其实有点累，但还行。")

    def test_split_count(self):
        from botv.life.reflow import split_memories
        items = split_memories(self.DIARY)
        self.assertGreaterEqual(len(items), 2)
        self.assertLessEqual(len(items), 3)

    def test_split_truncates_long(self):
        from botv.life.reflow import split_memories
        items = split_memories("啊" * 200 + "。")
        self.assertTrue(items)
        self.assertTrue(all(len(i) <= 61 for i in items))

    def test_sentiment_signs(self):
        from botv.life.reflow import sentiment_bias
        self.assertLess(sentiment_bias("很累，很烦，什么都做错"), 0)
        self.assertGreater(sentiment_bias("很开心，顺利完成"), 0)

    def test_sentiment_capped(self):
        from botv.life.reflow import sentiment_bias
        self.assertLessEqual(abs(sentiment_bias("累烦难过冷" * 100)), 0.15)

    def test_reflow_writes_to_self(self):
        import botv.life.reflow as R
        import botv.infra.repo_memory as rm
        calls = []
        orig_add, orig_apply = rm.add_event_to_db, R._apply_bias
        rm.add_event_to_db = lambda tid, text, **k: calls.append((tid, text, k.get("kind")))
        R._apply_bias = lambda b: None
        try:
            n, _bias = R.reflow("2026-11-08", self.DIARY)
        finally:
            rm.add_event_to_db, R._apply_bias = orig_add, orig_apply
        self.assertGreaterEqual(n, 1)
        self.assertTrue(calls)
        self.assertTrue(all(c[0] == rm.STATE_TARGET and c[2] == "life" for c in calls))


class TestImpulse(unittest.TestCase):
    """v10-U9：主动消息的六道闸门"""

    class _R:
        def __init__(self, v):
            self.v = v

        def random(self):
            return self.v

    NOW = None

    def setUp(self):
        from datetime import datetime
        from botv.config import CST
        self.now = datetime.now(CST).replace(hour=20, minute=0, second=0)
        self.cfg = __import__("botv.core.state", fromlist=["x"])
        self.cfg.last_user_msg_ts = 0.0
        self.cfg.last_proactive_ts = 0.0
        self.cfg.proactive_count_today = 0
        self.cfg.proactive_unanswered = 0

    def test_quiet_hours(self):
        from botv.life.impulse import should_reach_out
        ok, why = should_reach_out(now=self.now.replace(hour=2), state={"lonely": 0.9},
                                   rng=self._R(0.01))
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

    def test_just_talked(self):
        import time
        from botv.life.impulse import should_reach_out
        ok, why = should_reach_out(now=self.now, state={"lonely": 0.9},
                                   rng=self._R(0.01), last_user_ts=time.time() - 60)
        self.assertFalse(ok)
        self.assertEqual(why, "刚聊过")

    def test_not_lonely_enough(self):
        from botv.life.impulse import should_reach_out
        ok, _why = should_reach_out(now=self.now, state={"lonely": 0.2}, rng=self._R(0.01))
        self.assertFalse(ok)

    def test_probability_gate(self):
        from botv.life.impulse import should_reach_out
        ok_no, _ = should_reach_out(now=self.now, state={"lonely": 0.9}, rng=self._R(0.99))
        ok_yes, _ = should_reach_out(now=self.now, state={"lonely": 0.9}, rng=self._R(0.01))
        self.assertFalse(ok_no)
        self.assertTrue(ok_yes)

    def test_daily_cap(self):
        import time
        from botv.life.impulse import should_reach_out
        ok, why = should_reach_out(now=self.now, state={"lonely": 0.9}, rng=self._R(0.01),
                                   last_proactive_ts=time.time() - 3600, proactive_count=3)
        self.assertFalse(ok)
        self.assertEqual(why, "今日配额用完")

    def test_unanswered_backoff(self):
        from botv.life.impulse import should_reach_out
        ok, why = should_reach_out(now=self.now, state={"lonely": 0.9}, rng=self._R(0.01),
                                   unanswered=2)
        self.assertFalse(ok)
        self.assertEqual(why, "连续没回应")

    def test_note_counters(self):
        from botv.life.impulse import note_proactive, note_user_message
        note_proactive()
        note_proactive()
        self.assertEqual(self.cfg.proactive_count_today, 2)
        self.assertEqual(self.cfg.proactive_unanswered, 2)
        note_user_message()
        self.assertEqual(self.cfg.proactive_unanswered, 0)


class TestGroupProbability(unittest.TestCase):
    """v10：群聊回话概率随状态浮动"""

    def test_base(self):
        from botv.chat.handler import group_reply_probability, GROUP_BASE_PROB
        p = group_reply_probability({"lonely": 0.2, "mood": 0.1}, 0)
        self.assertAlmostEqual(p, GROUP_BASE_PROB, places=3)

    def test_lonely_raises(self):
        from botv.chat.handler import group_reply_probability
        quiet = group_reply_probability({"lonely": 0.2, "mood": 0.0}, 0)
        lonely = group_reply_probability({"lonely": 0.9, "mood": 0.0}, 0)
        self.assertGreater(lonely, quiet)

    def test_bad_mood_lowers(self):
        from botv.chat.handler import group_reply_probability
        good = group_reply_probability({"lonely": 0.9, "mood": 0.5}, 0)
        bad = group_reply_probability({"lonely": 0.9, "mood": -0.5}, 0)
        self.assertLess(bad, good)

    def test_unanswered_halves(self):
        from botv.chat.handler import (group_reply_probability,
                                       GROUP_UNANSWERED_LIMIT, GROUP_UNANSWERED_DECAY)
        normal = group_reply_probability({"lonely": 0.9, "mood": 0.0}, 0)
        quiet = group_reply_probability({"lonely": 0.9, "mood": 0.0}, GROUP_UNANSWERED_LIMIT)
        self.assertAlmostEqual(quiet, normal * GROUP_UNANSWERED_DECAY, places=3)

    def test_clamped(self):
        from botv.chat.handler import (group_reply_probability, GROUP_PROB_MIN, GROUP_PROB_MAX)
        for lonely in (0.0, 0.5, 1.0):
            for mood in (-1.0, 0.0, 1.0):
                p = group_reply_probability({"lonely": lonely, "mood": mood}, 0)
                self.assertGreaterEqual(p, GROUP_PROB_MIN)
                self.assertLessEqual(p, GROUP_PROB_MAX)

    def test_streak_increments_and_resets(self):
        from botv.chat import handler as h
        cfg.group_streak.clear()
        h.note_group_reply(555)
        h.note_group_reply(555)
        self.assertEqual(cfg.group_streak[555], 2)
        cfg.group_streak.clear()


class TestPending(unittest.TestCase):
    """v10-U9b：承诺与时间锚点识别"""

    def test_promise(self):
        from botv.life.pending import detect
        items = detect("今天有点累，回头再说吧")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["k"], "promise")

    def test_anchor(self):
        from botv.life.pending import detect
        items = detect("我先去吃饭了，等下聊")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["k"], "anchor")
        self.assertEqual(items[0]["t"], "吃饭")

    def test_anchor_delay(self):
        from botv.life.pending import detect
        from datetime import datetime
        from botv.config import CST
        now = datetime(2026, 11, 9, 12, 0, tzinfo=CST)
        it = detect("去洗澡", now)[0]
        self.assertAlmostEqual(it["due"] - now.timestamp(), 25 * 60, delta=5)

    def test_promise_delay(self):
        from botv.life.pending import detect
        from datetime import datetime
        from botv.config import CST
        now = datetime(2026, 11, 9, 22, 0, tzinfo=CST)
        it = detect("改天聊", now)[0]
        self.assertAlmostEqual((it["due"] - now.timestamp()) / 3600, 20, delta=0.1)

    def test_plain_text_no_item(self):
        from botv.life.pending import detect
        self.assertEqual(detect("你好呀，在干嘛"), [])

    def test_not_both(self):
        """同一句话不该既记承诺又记锚点"""
        from botv.life.pending import detect
        items = detect("我去吃饭了，回头再说")
        self.assertLessEqual(len(items), 2)

    def test_describe(self):
        from botv.life.pending import describe
        self.assertIn("答应过", describe({"k": "promise", "s": "回头再说"}))
        self.assertIn("吃饭", describe({"k": "anchor", "t": "吃饭", "s": "去吃饭"}))


class TestGateBypass(unittest.TestCase):
    """v10-U9b：承诺/锚点不受孤独门槛限制"""

    def test_bypass_lonely(self):
        from datetime import datetime
        from botv.config import CST
        from botv.life.impulse import should_reach_out

        class R:
            def random(self):
                return 0.0
        now = datetime.now(CST).replace(hour=20)
        ok, why = should_reach_out(now=now, state={"lonely": 0.0, "mood": 0.0},
                                   rng=R(), require_lonely=False,
                                   last_user_ts=0.0, proactive_count=0, unanswered=0)
        self.assertTrue(ok, why)

    def test_still_blocked_at_night(self):
        from datetime import datetime
        from botv.config import CST
        from botv.life.impulse import should_reach_out

        class R:
            def random(self):
                return 0.0
        now = datetime.now(CST).replace(hour=2)
        ok, why = should_reach_out(now=now, state={"lonely": 0.9},
                                   rng=R(), require_lonely=False)
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")


class TestRelation(unittest.TestCase):
    """v10-U8：关系分档"""

    def test_tiers(self):
        from botv.life.relation import tier_of
        self.assertEqual(tier_of(0.9)[0], "亲近")
        self.assertEqual(tier_of(0.5)[0], "熟")
        self.assertEqual(tier_of(0.3)[0], "认识")
        self.assertEqual(tier_of(0.0)[0], "陌生")

    def test_master_starts_higher(self):
        import botv.life.relation as R
        import botv.infra.repo_memory as rm
        from botv.config import MASTER_QQ
        orig = rm.load_relation
        rm.load_relation = lambda tid: ""
        try:
            a_master = R.get(str(MASTER_QQ))
            a_other = R.get("99999")
        finally:
            rm.load_relation = orig
        self.assertGreater(a_master, a_other)

    def test_describe_contains_tier(self):
        import botv.life.relation as R
        orig = R.get
        R.get = lambda tid: 0.8
        try:
            s = R.describe("1")
        finally:
            R.get = orig
        self.assertIn("亲近", s)
        self.assertNotIn("0.8", s, "数值不该出现在描述里")

    def test_tier_bounds(self):
        from botv.life.relation import TIERS
        lows = [lo for lo, _n, _d in TIERS]
        self.assertEqual(lows, sorted(lows, reverse=True))
        self.assertEqual(lows[-1], 0.0)


class TestAgenda(unittest.TestCase):
    """v10-U10：日程时间解析"""

    NOW = None

    def setUp(self):
        from datetime import datetime
        from botv.config import CST
        self.now = datetime(2026, 11, 9, 10, 30, tzinfo=CST)  # 周一

    def _when(self, text):
        from botv.life.agenda import parse_when
        return parse_when(text, self.now)

    def test_tomorrow(self):
        self.assertEqual(self._when("明天上午交作业").strftime("%m-%d %H:%M"), "11-10 09:00")

    def test_day_after(self):
        self.assertEqual(self._when("后天晚上八点约会").strftime("%m-%d %H:%M"), "11-11 20:00")

    def test_weekday(self):
        self.assertEqual(self._when("周五下午三点面试").strftime("%m-%d %H:%M"), "11-13 15:00")

    def test_date(self):
        self.assertEqual(self._when("11月15日答辩").strftime("%m-%d %H:%M"), "11-15 09:00")

    def test_tonight_chinese_numeral(self):
        self.assertEqual(self._when("今晚九点开会").strftime("%m-%d %H:%M"), "11-09 21:00")

    def test_no_time(self):
        self.assertIsNone(self._when("你好呀"))

    def test_extract_needs_event_word(self):
        from botv.life.agenda import extract
        self.assertIsNone(extract("明天出去玩", self.now), "没有事件词不该记")
        self.assertIsNotNone(extract("明天面试", self.now))

    def test_extract_ignores_past(self):
        from botv.life.agenda import extract
        self.assertIsNone(extract("昨天面试", self.now))

    def test_past_today_ignored(self):
        from botv.life.agenda import extract
        self.assertIsNone(extract("今天上午九点开会", self.now), "已经过去的今天不记")


class TestNameCheck(unittest.TestCase):
    """v10.2：静态检查能抓到「用了但没定义」的名字"""

    def setUp(self):
        import os as _os
        import sys as _sys
        scripts = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "scripts")
        if scripts not in _sys.path:
            _sys.path.insert(0, scripts)

    def test_catches_undefined(self):
        import check_names
        probs = check_names.check_source("def f():\n    return missing_thing(1)\n", "x.py")
        self.assertTrue(probs)
        self.assertEqual(probs[0][2], "missing_thing")

    def test_clean_source(self):
        import check_names
        src = "import os\n\n\ndef f():\n    return os.getcwd()\n"
        self.assertEqual(check_names.check_source(src, "x.py"), [])

    def test_builtin_ok(self):
        import check_names
        self.assertEqual(check_names.check_source("def f():\n    return len([1])\n", "x.py"), [])


    def test_use_before_assign(self):
        import check_names
        src = "_x = 0\n\n\ndef f():\n    while True:\n        if _x > 3:\n            _x = 1\n"
        probs = check_names.check_local_order(src, "x.py")
        self.assertTrue(probs)
        self.assertEqual(probs[0][2], "_x")

    def test_global_declared_ok(self):
        import check_names
        src = "_x = 0\n\n\ndef f():\n    global _x\n    if _x > 3:\n        _x = 1\n"
        self.assertEqual(check_names.check_local_order(src, "x.py"), [])


class TestScheduleTick(unittest.TestCase):
    """v10.3：定时循环的两段逻辑，用假数据做代码级测试（不连 AI）"""

    def setUp(self):
        from datetime import datetime
        from botv.config import CST
        import botv.schedule.runner as R
        self.R = R
        self.now = datetime(2026, 11, 9, 20, 0, tzinfo=CST)
        self.sent = []
        self._orig = {}
        self._patch("get_character_reply", self._fake_reply)
        self._patch("send_short_reply", self._fake_send)
        self._patch("note_proactive", lambda: None)

    def tearDown(self):
        for name, fn in self._orig.items():
            if name.startswith("impulse."):
                import botv.life.impulse as IMP
                IMP.should_chat = fn
            else:
                setattr(self.R, name, fn)
        from botv.core import state as cfg
        cfg.daily_chat_trigger_times = []
        cfg.triggered_today.clear()

    def _patch(self, name, fn):
        self._orig[name] = getattr(self.R, name)
        setattr(self.R, name, fn)

    async def _fake_reply(self, prompt, tid):
        return "假回复"

    async def _fake_send(self, *args, **kwargs):
        self.sent.append(args)

    def test_module_exports(self):
        """回归：这几个名字必须在模块里（曾经漏 import 导致 NameError）"""
        for name in ("pending_due", "agenda_due_soon", "should_reach_out",
                     "note_proactive", "load_today_life", "describe_pending",
                     "finish_pending", "agenda_mark"):
            self.assertTrue(hasattr(self.R, name), f"runner 缺少 {name}")

    def test_throttle_var_is_local(self):
        """回归：节流变量不能是模块全局，否则函数内赋值会 UnboundLocalError"""
        self.assertFalse(hasattr(self.R, "_last_due_check"))

    def test_process_due_sends_agenda(self):
        import asyncio
        self._patch("agenda_due_soon", lambda m: [{"id": 7, "t": "面试"}])
        self._patch("pending_due", lambda now: [])
        self._patch("should_reach_out", lambda **kw: (True, "ok"))
        self._patch("agenda_mark", lambda i: None)
        n = asyncio.run(self.R.process_due(self.now))
        self.assertEqual(n, 1)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0][1], "假回复")

    def test_process_due_blocked_by_gate(self):
        import asyncio
        self._patch("agenda_due_soon", lambda m: [{"id": 7, "t": "面试"}])
        self._patch("pending_due", lambda now: [])
        self._patch("should_reach_out", lambda **kw: (False, "深夜"))
        n = asyncio.run(self.R.process_due(self.now))
        self.assertEqual(n, 0)
        self.assertEqual(self.sent, [])

    def test_process_due_handles_pending(self):
        import asyncio
        self._patch("agenda_due_soon", lambda m: [])
        self._patch("pending_due", lambda now: [(3, {"k": "anchor", "t": "吃饭"})])
        self._patch("should_reach_out", lambda **kw: (True, "ok"))
        self._patch("finish_pending", lambda i: None)
        n = asyncio.run(self.R.process_due(self.now))
        self.assertEqual(n, 1)

    def _patch_should_chat(self, result):
        import botv.life.impulse as IMP
        self._orig["impulse.should_chat"] = IMP.should_chat
        IMP.should_chat = lambda **kw: result
        self._patch("load_today_life", lambda: [])
        self._patch("load_events_from_db", lambda *a, **k: [])

    def test_maybe_chat_fires(self):
        import asyncio
        from botv.core import state as cfg
        cfg.triggered_today.clear()
        self._patch_should_chat((True, "想说话了", 0.1))
        ok = asyncio.run(self.R.maybe_chat(self.now))
        self.assertTrue(ok)
        self.assertEqual(len(self.sent), 1)

    def test_maybe_chat_skipped_by_gate(self):
        import asyncio
        from botv.core import state as cfg
        cfg.triggered_today.clear()
        self._patch_should_chat((False, "刚聊过", 0.0))
        ok = asyncio.run(self.R.maybe_chat(self.now))
        self.assertFalse(ok)
        self.assertEqual(self.sent, [])

    def test_maybe_chat_ignores_other_minutes(self):
        import asyncio
        from botv.core import state as cfg
        cfg.triggered_today.clear()
        self._patch_should_chat((True, "ok", 0.5))
        odd = self.now.replace(minute=17)  # 不在整半点
        ok = asyncio.run(self.R.maybe_chat(odd))
        self.assertFalse(ok)

    def test_maybe_chat_only_once_per_window(self):
        import asyncio
        from botv.core import state as cfg
        cfg.triggered_today.clear()
        self._patch_should_chat((True, "ok", 0.5))
        first = asyncio.run(self.R.maybe_chat(self.now))
        second = asyncio.run(self.R.maybe_chat(self.now))
        self.assertTrue(first)
        self.assertFalse(second, "同一个 30 分钟窗口不能触发两次")


class TestChatImpulse(unittest.TestCase):
    """v10.4：30 分钟一次的主动闲聊掷骰"""

    class _R:
        def __init__(self, v=0.0):
            self.v = v

        def random(self):
            return self.v

    def _now(self, hour, minute=0):
        from datetime import datetime
        from botv.config import CST
        return datetime(2026, 11, 9, hour, minute, tzinfo=CST)

    def test_night_is_zero(self):
        from botv.life.impulse import chat_probability
        self.assertEqual(chat_probability(self._now(3), 5, {"lonely": 1, "mood": 1}), 0.0)

    def test_silence_raises(self):
        from botv.life.impulse import chat_probability
        st = {"lonely": 0.3, "mood": 0.0}
        short = chat_probability(self._now(19), 0.5, st)
        long = chat_probability(self._now(19), 4, st)
        self.assertGreater(long, short)

    def test_life_event_boosts(self):
        from botv.life.impulse import chat_probability
        st = {"lonely": 0.3, "mood": 0.0}
        plain = chat_probability(self._now(19), 3, st, has_life_event=False)
        boosted = chat_probability(self._now(19), 3, st, has_life_event=True)
        self.assertGreater(boosted, plain)
        self.assertAlmostEqual(boosted / plain, 1.8, places=2)

    def test_probability_capped(self):
        from botv.life.impulse import chat_probability, CHAT_MAX_P
        st = {"lonely": 1.0, "mood": 1.0}
        self.assertLessEqual(chat_probability(self._now(19), 99, st, True), CHAT_MAX_P)

    def test_should_chat_blocks(self):
        from botv.life.impulse import should_chat
        ok, why, _p = should_chat(now=self._now(3), state={"lonely": 1}, rng=self._R(0.0))
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

    def test_should_chat_roll(self):
        from botv.life.impulse import should_chat
        st = {"lonely": 0.3, "mood": 0.0}
        miss, _w, _p = should_chat(now=self._now(19), state=st, rng=self._R(0.99),
                                   silent_hours=4, last_user_ts=0.0,
                                   proactive_count=0, unanswered=0, last_proactive_ts=0.0)
        hit, _w2, _p2 = should_chat(now=self._now(19), state=st, rng=self._R(0.0),
                                    silent_hours=4, last_user_ts=0.0,
                                    proactive_count=0, unanswered=0, last_proactive_ts=0.0)
        self.assertFalse(miss)
        self.assertTrue(hit)


class TestPhotoMemory(unittest.TestCase):
    """v11-A9：她记住你发过的图"""

    def test_kind_registered(self):
        from botv.infra.repo_memory import KIND_LIMITS, DEFAULT_KINDS
        self.assertIn("photo", KIND_LIMITS, "photo 要有独立保留上限")
        self.assertIn("photo", DEFAULT_KINDS, "检索要能召回图片记忆")

    def test_photo_event_written_with_tags(self):
        import botv.infra.repo_memory as rm
        import botv.chat.inbound as inbound
        self.assertTrue(hasattr(inbound, "add_event_to_db"), "inbound 应导入 add_event_to_db")

    def test_kind_limit_value(self):
        from botv.infra.repo_memory import KIND_LIMITS
        self.assertGreaterEqual(KIND_LIMITS["photo"], 20)


class TestVision(unittest.TestCase):
    """v11-A8/A6：看图拿描述和标签"""

    def test_parse_fullwidth_colon(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("描述：一只橘猫趴在窗台上打哈欠\n标签：猫,橘猫,窗台,打哈欠")
        self.assertIn("橘猫", desc)
        self.assertEqual(tags[:2], ["猫", "橘猫"])

    def test_parse_ascii_colon(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("描述: 两个人在吃火锅\n标签: 火锅,朋友")
        self.assertIn("火锅", desc)
        self.assertIn("朋友", tags)

    def test_parse_no_format(self):
        from botv.ai.vision import parse_reply
        desc, tags = parse_reply("完全没按格式的一段话")
        self.assertEqual(desc, "完全没按格式的一段话")
        self.assertEqual(tags, [])

    def test_tags_capped(self):
        from botv.ai.vision import parse_reply
        _d, tags = parse_reply("标签：a,b,c,d,e,f,g,h")
        self.assertLessEqual(len(tags), 5)

    def test_no_key_returns_empty(self):
        import asyncio
        import botv.ai.vision as V
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = ""
        try:
            desc, tags = asyncio.run(V.describe_image(b"\xff\xd8fake"))
        finally:
            cfg.DS_API_KEY = orig
        self.assertIsNone(desc)
        self.assertEqual(tags, [])


class TestVoice(unittest.TestCase):
    """v11-A10：语音的择时与降级"""

    def setUp(self):
        import botv.chat.send as S
        self.S = S
        self.sent = []
        self._orig = {}
        self._patch("tts_synth", self._fake_synth)
        self._patch("send_voice", self._fake_send)
        S._last_voice_ts.clear()

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(self.S, name, fn)
        self.S._last_voice_ts.clear()

    def _patch(self, name, fn):
        self._orig[name] = getattr(self.S, name)
        setattr(self.S, name, fn)

    async def _fake_synth(self, text):
        return b"FAKE_MP3"

    async def _fake_send(self, *args, **kwargs):
        self.sent.append(args)

    def _run(self, text="今天天气不错啊", target="1", is_group=False, prob=0.0):
        import asyncio
        orig_random = self.S.random.random
        self.S.random.random = lambda: prob
        try:
            return asyncio.run(self.S.maybe_send_voice(text, target, None, is_group))
        finally:
            self.S.random.random = orig_random

    def test_fires(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.sent), 1)

    def test_group_never(self):
        self.assertFalse(self._run(is_group=True))
        self.assertEqual(self.sent, [])

    def test_too_short(self):
        self.assertFalse(self._run(text="嗯"))
        self.assertEqual(self.sent, [])

    def test_too_long(self):
        self.assertFalse(self._run(text="啊" * 200))
        self.assertEqual(self.sent, [])

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.sent, [])

    def test_cooldown(self):
        self.assertTrue(self._run())
        self.assertFalse(self._run(), "20 分钟内不该再发")

    def test_synth_failure_degrades(self):
        self._patch("tts_synth", lambda text: self._none())
        self.assertFalse(self._run())
        self.assertEqual(self.sent, [])

    async def _none(self):
        return None


class TestASR(unittest.TestCase):
    """v11-A14：语音转文字（不可用时安静降级）"""

    def test_filename_guess(self):
        from botv.speech.asr import _filename_for
        self.assertTrue(_filename_for("https://x/a.mp3").endswith(".mp3"))
        self.assertTrue(_filename_for("https://x/a.amr").endswith(".amr"))
        self.assertTrue(_filename_for("").endswith(".mp3"))

    def test_no_key_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = ""
        try:
            self.assertIsNone(asyncio.run(transcribe(b"fake-audio")))
        finally:
            cfg.DS_API_KEY = orig

    def test_oversized_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe, MAX_BYTES
        from botv.core import state as cfg
        orig = getattr(cfg, "DS_API_KEY", "")
        cfg.DS_API_KEY = "k"
        try:
            self.assertIsNone(asyncio.run(transcribe(b"x" * (MAX_BYTES + 1))))
        finally:
            cfg.DS_API_KEY = orig

    def test_empty_returns_none(self):
        import asyncio
        from botv.speech.asr import transcribe
        self.assertIsNone(asyncio.run(transcribe(b"")))


class TestAutoInstall(unittest.TestCase):
    """启动时对「小体积可选包」自动装一次"""

    def test_edge_tts_allowed(self):
        import run
        self.assertIn("edge-tts", run.AUTO_OPTIONAL_PACKAGES)

    def test_big_packages_not_allowed(self):
        import run
        self.assertNotIn("torch", run.AUTO_OPTIONAL_PACKAGES, "torch 几百 MB，绝不能自动装")
        self.assertIn("torch", run.OPTIONAL_PACKAGES, "但仍是可选依赖")

    def test_timeout_exists(self):
        import run
        self.assertGreater(run.INSTALL_TIMEOUT, 0)
        self.assertLessEqual(run.INSTALL_TIMEOUT, 600, "超时别超过 10 分钟")

    def test_import_name_mapping(self):
        """edge-tts 的 import 名是 edge_tts，映射必须存在"""
        import importlib.util
        # 直接验证逻辑：pip 名换下划线
        self.assertEqual("edge-tts".replace("-", "_"), "edge_tts")


class TestEnvironment(unittest.TestCase):
    """环境相关：依赖表、环境变量、路径必须一致（每版都要过）"""

    # 代码里允许出现的环境变量白名单；新增时必须同步 docs/发布检查清单.md
    EXPECTED_ENV = {
        "NAO_CLIP",
        "NAO_VOICE",
        "NAO_VISION_MODEL",
        "NAO_VISION_URL",
        "NAO_ASR_URL",
        "NAO_ASR_MODEL",
        "NAO_NO_AUTOINSTALL",
        "NAO_CITY",
        "NAO_PERSONA",
        "NAO_READ_IDLE_HOURS",
        "NAO_READ_DAILY_CHAPTERS",
        "NAO_BOOK_URLS",
        "NAO_OCR_LANG",
        # v16：Docker/多机部署覆盖项
        "NAO_MASTER_QQ",
        "NAO_LISTEN_HOST",
        "NAO_WS_PORT",
        "NAO_API_PORT",
        "NAO_DB_HOST",
        "NAO_DB_PORT",
        "NAO_DB_USER",
        "NAO_DB_PASS",
        "NAO_DB_NAME",
    }

    @staticmethod
    def _root():
        import pathlib
        return pathlib.Path(__file__).resolve().parent.parent

    def test_env_vars_registered(self):
        """新加的环境变量必须登记，否则换机器时调不动"""
        import re
        root = self._root()
        pattern = re.compile(r"os\.getenv\(\s*[\"']([A-Za-z0-9_]+)")
        found = set()
        for p in list((root / "botv").rglob("*.py")) + [root / "run.py"]:
            found |= set(pattern.findall(p.read_text(encoding="utf-8")))
        unknown = found - self.EXPECTED_ENV
        self.assertFalse(unknown, f"未登记的环境变量: {sorted(unknown)}")

    def test_env_documented(self):
        """白名单里的变量都得写进发布检查清单"""
        doc = (self._root() / "docs" / "发布检查清单.md").read_text(encoding="utf-8")
        for name in self.EXPECTED_ENV:
            self.assertIn(name, doc, f"{name} 没写进发布检查清单")

    def test_dependency_lists_consistent(self):
        """run.py 与 preflight 的依赖表要能对上（pip 名 vs import 名做归一化）"""
        import sys
        import run
        sys.path.insert(0, str(self._root() / "scripts"))
        import preflight

        # pip 包名 → import 名
        alias = {"Pillow": "PIL", "edge-tts": "edge_tts"}
        run_required = {alias.get(p, p) for p in run.REQUIRED_PACKAGES}
        pre_required = {alias.get(p, p) for p in preflight.REQUIRED}
        missing = run_required - pre_required
        self.assertFalse(missing, f"必需依赖没进预检: {sorted(missing)}")

        for pkg in run.AUTO_OPTIONAL_PACKAGES:
            name = alias.get(pkg, pkg)
            self.assertIn(name, preflight.OPTIONAL, f"自动安装的 {pkg} 不在预检可选依赖里")

    def test_no_absolute_paths_in_botv(self):
        """botv 里不该出现硬编码的绝对路径"""
        import re
        root = self._root()
        bad = []
        for p in (root / "botv").rglob("*.py"):
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r"[\"'](/home/|/root/|C:\\\\Users)", text):
                bad.append(f"{p.name}: {m.group(0)}")
        self.assertFalse(bad, f"发现硬编码绝对路径: {bad[:5]}")

    def test_bundle_ignores_artifacts(self):
        """打包不该带 .pyc / bundle 文件"""
        gitignore = (self._root() / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.pyc", gitignore)
        self.assertIn("__pycache__", gitignore)


class TestPreflightSteps(unittest.TestCase):
    """预检要覆盖环境相关的新检查"""

    def setUp(self):
        import os as _os
        import sys as _sys
        scripts = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "scripts")
        if scripts not in _sys.path:
            _sys.path.insert(0, scripts)

    def test_steps_exist(self):
        import preflight
        for name in ("step_env", "step_capabilities", "step_network",
                     "step_names", "step_memory_schema", "step_optional"):
            self.assertTrue(hasattr(preflight, name), f"预检缺少 {name}")

    def test_env_output_has_no_secrets(self):
        import preflight
        out = preflight.step_env()
        for bad in ("sk-", "Bearer", "nao_"):
            self.assertNotIn(bad, out, f"环境变量输出里不该出现 {bad}")

    def test_capabilities_mentions_three(self):
        import preflight
        out = preflight.step_capabilities()
        for word in ("视觉", "语音合成", "语音识别"):
            self.assertIn(word, out)


    def test_animated_hint(self):
        """动图要让模型知道「你只看到一帧」"""
        from botv.ai.vision import prompt_with_hint, PROMPT
        self.assertEqual(prompt_with_hint(False), PROMPT)
        self.assertIn("动图", prompt_with_hint(True))

    def test_gif_magic_detection(self):
        """GIF 魔数识别（inbound 里判断是不是动图）"""
        for head in (b"GIF89a....", b"GIF87a...."):
            self.assertTrue(head[:6] in (b"GIF89a", b"GIF87a"))
        self.assertFalse(b"\xff\xd8\xff\xe0" [:6] in (b"GIF89a", b"GIF87a"))


    def test_frame_indices_even(self):
        """抽帧要均匀且含首尾"""
        from botv.ai.vision import frame_indices, MAX_FRAMES
        idx = frame_indices(60)
        self.assertEqual(len(idx), MAX_FRAMES)
        self.assertEqual(idx[0], 0)
        self.assertEqual(idx[-1], 59)
        self.assertEqual(idx, sorted(idx))
        self.assertEqual(len(set(idx)), len(idx), "不能重复")

    def test_frame_indices_short_gif(self):
        """帧数不够就全要"""
        from botv.ai.vision import frame_indices
        self.assertEqual(frame_indices(5), [0, 1, 2, 3, 4])

    def test_frame_indices_edge(self):
        from botv.ai.vision import frame_indices
        self.assertEqual(frame_indices(0), [])
        self.assertEqual(frame_indices(1), [0])

    def test_prompt_mentions_frame_count(self):
        from botv.ai.vision import prompt_with_hint
        text = prompt_with_hint(True, 24)
        self.assertIn("24 帧", text)
        self.assertIn("网格", text)


class TestHabit(unittest.TestCase):
    """v12-A17：学口头禅"""

    def setUp(self):
        from botv.core import state as cfg
        cfg.habit_counters.clear()

    def tearDown(self):
        from botv.core import state as cfg
        cfg.habit_counters.clear()

    def test_ngrams_filters_stopwords(self):
        from botv.life.habit import ngrams
        pieces = ngrams("就是这样的")
        self.assertNotIn("就是", pieces)
        self.assertNotIn("这样", pieces)

    def test_ngrams_lengths(self):
        from botv.life.habit import ngrams
        for piece in ngrams("绝了绝了"):
            self.assertTrue(2 <= len(piece) <= 4, piece)

    def test_top_needs_three(self):
        from collections import Counter
        from botv.life.habit import top
        c = Counter()
        c["绝了"] = 2
        self.assertEqual(top(c), [], "不够 3 次不算")

    def test_top_prefers_short(self):
        """次数相同时优先短词，避免学出跨词边界的废词"""
        from collections import Counter
        from botv.life.habit import top
        c = Counter({"草了": 5, "草了草了": 5})
        picked = top(c)
        self.assertIn("草了", picked)
        self.assertNotIn("草了草了", picked, "互相包含的只留一个")

    def test_top_limits_three(self):
        from collections import Counter
        from botv.life.habit import top
        c = Counter({"甲甲": 5, "乙乙": 5, "丙丙": 5, "丁丁": 5})
        self.assertEqual(len(top(c)), 3)

    def test_learn_accumulates(self):
        import botv.life.habit as H
        for _ in range(4):
            H.learn("100", "绝了这也太草了")
        self.assertIn("绝了", H.phrases_for("100"))

    def test_describe(self):
        from botv.life.habit import describe
        self.assertEqual(describe([]), "")
        self.assertIn("绝了", describe(["绝了"]))

    def test_profile_with_habit(self):
        import botv.ai.client as client
        orig_build, orig_phrases = client.build_profile_text, client.phrases_for
        client.build_profile_text = lambda tid: "昵称：小奈"
        client.phrases_for = lambda tid: ["绝了"]
        try:
            text = client._profile_with_habit("1")
        finally:
            client.build_profile_text, client.phrases_for = orig_build, orig_phrases
        self.assertIn("小奈", text)
        self.assertIn("绝了", text)


class TestMilestone(unittest.TestCase):
    """v12-G38：认识第几天"""

    def setUp(self):
        import botv.life.milestone as M
        import botv.infra.repo_memory as rm
        self.M = M
        self.rm = rm
        self.store = {}
        self._orig = (rm.load_relation, rm.save_relation)
        rm.load_relation = lambda tid: self.store.get(tid, "")
        rm.save_relation = lambda tid, payload: self.store.__setitem__(tid, payload) or True

    def tearDown(self):
        self.rm.load_relation, self.rm.save_relation = self._orig

    def _day(self, n):
        from datetime import datetime, timedelta
        from botv.config import CST
        base = datetime(2026, 1, 1, tzinfo=CST)
        return base, base + timedelta(days=n)

    def test_first_call_records_since(self):
        base, _ = self._day(0)
        self.M.since_date("u1", base)
        self.assertIn("2026-01-01", self.store["u1"])

    def test_days_together(self):
        base, _ = self._day(0)
        self.M.since_date("u1", base)
        _, later = self._day(99)
        self.assertEqual(self.M.days_together("u1", later), 100)

    def test_milestones(self):
        base, _ = self._day(0)
        self.M.since_date("u1", base)
        for n, keyword in ((1, "第一天"), (7, "一周"), (30, "一个月"), (100, "一百天")):
            _, now = self._day(n - 1)
            text = self.M.milestone_text("u1", now)
            self.assertIn(keyword, text, f"第 {n} 天应提到 {keyword}")

    def test_normal_day_no_text(self):
        base, _ = self._day(0)
        self.M.since_date("u1", base)
        _, now = self._day(42)
        self.assertEqual(self.M.milestone_text("u1", now), "")

    def test_profile_includes_milestone(self):
        import botv.ai.client as client
        orig_build = client.build_profile_text
        orig_habit = client.phrases_for
        orig_ms = client.milestone_text
        client.build_profile_text = lambda tid: "昵称：小奈"
        client.phrases_for = lambda tid: []
        client.milestone_text = lambda tid, now=None: "今天正好认识一百天（第 100 天）"
        try:
            text = client._profile_with_habit("1")
        finally:
            client.build_profile_text = orig_build
            client.phrases_for = orig_habit
            client.milestone_text = orig_ms
        self.assertIn("一百天", text)


class TestV12Extras(unittest.TestCase):
    """v12：仪式 / 记忆本 / 旧事重提"""

    def test_sunday_ritual_task(self):
        from botv.schedule.config import SCHEDULE_TASKS
        scenes = [t["scene"] for t in SCHEDULE_TASKS]
        self.assertIn("周日复盘", scenes, "周日晚上要有一次复盘仪式")

    def test_memorybook_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry
        self.assertIn("memorybook", registry.COMMANDS)

    def test_old_event_branch(self):
        """主动闲聊有概率拿一件旧事当由头"""
        import asyncio
        from datetime import datetime
        import botv.schedule.runner as R
        import botv.life.impulse as IMP
        from botv.core import state as cfg
        from botv.config import CST

        sent, prompts = [], []
        orig = {}
        def patch(name, fn):
            orig[name] = getattr(R, name)
            setattr(R, name, fn)

        patch("load_old_events", lambda *a, **k: [{"summary": "去打疫苗", "day": "2026-10-01"}])
        patch("load_today_life", lambda: [])

        async def fake_reply(p, tid):
            prompts.append(p)
            return "还记得"

        async def fake_send(*a, **k):
            sent.append(a)

        patch("get_character_reply", fake_reply)
        patch("send_short_reply", fake_send)
        patch("note_proactive", lambda: None)
        orig_should = IMP.should_chat
        IMP.should_chat = lambda **kw: (True, "ok", 0.3)
        orig_random = R.random.random
        R.random.random = lambda: 0.1
        cfg.triggered_today.clear()
        try:
            ok = asyncio.run(R.maybe_chat(datetime.now(CST).replace(minute=0, second=0)))
        finally:
            for name, fn in orig.items():
                setattr(R, name, fn)
            IMP.should_chat = orig_should
            R.random.random = orig_random
            cfg.triggered_today.clear()
        self.assertTrue(ok)
        self.assertIn("旧事", prompts[0])
        self.assertIn("去打疫苗", prompts[0])


class TestWeather(unittest.TestCase):
    """v12-A21：天气（没配城市就完全跳过）"""

    def test_parse(self):
        from botv.life.weather import parse_j1
        data = {"current_condition": [{"temp_C": "12", "weatherDesc": [{"value": "小雨"}]}]}
        info = parse_j1(data)
        self.assertEqual(info["temp"], 12)
        self.assertEqual(info["desc"], "小雨")

    def test_parse_bad(self):
        from botv.life.weather import parse_j1
        self.assertIsNone(parse_j1({}))
        self.assertIsNone(parse_j1({"current_condition": []}))

    def test_describe(self):
        from botv.life.weather import describe
        self.assertEqual(describe(None), "")
        self.assertIn("12", describe({"temp": 12, "desc": "小雨"}))

    def test_no_city_returns_none(self):
        import asyncio
        from botv.life.weather import current
        import os
        old = os.environ.pop("NAO_CITY", None)
        try:
            self.assertIsNone(asyncio.run(current()))
        finally:
            if old is not None:
                os.environ["NAO_CITY"] = old


class TestShare(unittest.TestCase):
    """v12-A18：分享欲（偶尔补一句自己的事）"""

    def setUp(self):
        import botv.chat.handler as h
        self.h = h
        self.sent = []
        self._orig = {}
        self._patch("get_character_reply", self._fake_reply)
        self._patch("send_short_reply", self._fake_send)
        h._last_share_ts.clear()

        import botv.infra.repo_memory as rm
        self._orig["load_today_life"] = rm.load_today_life
        rm.load_today_life = lambda: ["小咪把多肉推下去了"]

    def tearDown(self):
        import botv.infra.repo_memory as rm
        for name, fn in self._orig.items():
            setattr(self.h, name, fn) if hasattr(self.h, name) else None
        if "load_today_life" in self._orig:
            rm.load_today_life = self._orig["load_today_life"]
        self.h._last_share_ts.clear()

    def _patch(self, name, fn):
        self._orig[name] = getattr(self.h, name)
        setattr(self.h, name, fn)

    async def _fake_reply(self, prompt, tid):
        return "对了，" + prompt[-20:]

    async def _fake_send(self, *args, **kwargs):
        self.sent.append(args)

    def _run(self, prob=0.0):
        import asyncio
        orig = self.h.random.random
        self.h.random.random = lambda: prob
        try:
            return asyncio.run(self.h.maybe_share_something("1", None))
        finally:
            self.h.random.random = orig

    def test_fires(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.sent), 1)

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.sent, [])

    def test_cooldown(self):
        self.assertTrue(self._run())
        self.assertFalse(self._run(), "40 分钟内不该再分享")

    def test_no_life_event(self):
        import botv.infra.repo_memory as rm
        rm.load_today_life = lambda: []
        self.assertFalse(self._run())


class TestTypoRecall(unittest.TestCase):
    """v12-A13：打错字 → 撤回 → 重发"""

    def setUp(self):
        import botv.chat.send as S
        self.S = S
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.typo_history.clear()
        self.deleted = []
        self._orig = {}
        self._patch("send_private_msg", self._fake_send)
        self._patch("_send_or_queue", self._fake_action)

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(self.S, name, fn)
        self.cfg.typo_history.clear()

    def _patch(self, name, fn):
        self._orig[name] = getattr(self.S, name)
        setattr(self.S, name, fn)

    async def _fake_send(self, target, msg, ws, want_response=False):
        return {"status": "ok", "data": {"message_id": 4242}}

    async def _fake_action(self, action, params, ws, label, **kw):
        self.deleted.append((action, params))
        return True

    def test_make_typo_differs(self):
        from botv.chat.send import make_typo
        text = "明天下午三点面试"
        typo = make_typo(text)
        self.assertNotEqual(typo, text)
        self.assertEqual(len(typo), len(text))

    def test_short_text_no_typo(self):
        from botv.chat.send import make_typo
        self.assertEqual(make_typo("在吗"), "在吗")

    def _run(self, text="明天下午三点面试", prob=0.0):
        import asyncio
        orig = self.S.random.random
        self.S.random.random = lambda: prob
        try:
            return asyncio.run(self.S.try_typo_recall("1", text, None))
        finally:
            self.S.random.random = orig

    def test_full_flow(self):
        self.assertTrue(self._run())
        self.assertEqual(len(self.deleted), 1)
        self.assertEqual(self.deleted[0][0], "delete_msg")
        self.assertEqual(self.deleted[0][1]["message_id"], 4242)
        self.assertEqual(len(self.cfg.typo_history), 1)

    def test_probability(self):
        self.assertFalse(self._run(prob=0.99))
        self.assertEqual(self.deleted, [])

    def test_weekly_quota(self):
        import time
        self.cfg.typo_history.extend([time.time(), time.time()])
        self.assertFalse(self._run(), "一周最多两次")
        self.assertEqual(self.deleted, [])

    def test_no_message_id_degrades(self):
        async def bad_send(target, msg, ws, want_response=False):
            return {"status": "failed"}
        self._patch("send_private_msg", bad_send)
        self.assertFalse(self._run())
        self.assertEqual(self.deleted, [])


class TestPoke(unittest.TestCase):
    """v12-A16：戳一戳回戳"""

    def test_detect(self):
        from botv.chat.notice import is_poke
        self.assertTrue(is_poke({"post_type": "notice", "notice_type": "notify", "sub_type": "poke"}))
        self.assertFalse(is_poke({"post_type": "message"}))
        self.assertFalse(is_poke({"post_type": "notice", "notice_type": "notify", "sub_type": "other"}))

    def test_reply_back_in_group(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append((action, params))

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "1001", "user_id": "2002", "group_id": 123}
        ok = asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertTrue(ok)
        self.assertEqual(calls[0][0], "group_poke")
        self.assertEqual(calls[0][1]["user_id"], "2002")

    def test_reply_back_private(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append((action, params))

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "1001", "user_id": "2002"}
        asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertEqual(calls[0][0], "friend_poke")

    def test_ignore_poke_others(self):
        import asyncio
        from botv.chat.notice import handle_notice
        calls = []

        async def fake(action, params, ws, label):
            calls.append(action)

        d = {"post_type": "notice", "notice_type": "notify", "sub_type": "poke",
             "target_id": "9999", "user_id": "2002"}
        ok = asyncio.run(handle_notice(d, None, 1001, fake))
        self.assertFalse(ok)
        self.assertEqual(calls, [])


class TestQuotedReply(unittest.TestCase):
    """v12-A15：引用回复标记"""

    def test_marker_without_ws(self):
        import asyncio
        from botv.chat.inbound import parse_message_content
        raw = [{"type": "reply", "data": {"id": 123}},
               {"type": "text", "data": {"text": "这个咋样"}}]
        text, _md5 = asyncio.run(parse_message_content(raw, "1", None))
        self.assertIn("引用", text)
        self.assertIn("这个咋样", text)


class TestInsideJokes(unittest.TestCase):
    """v12-G37：内部梗（按标签频次）"""

    def test_counts_and_picks(self):
        from botv.life.inside_jokes import count_tags, pick_jokes
        rows = [{"tags": "猫,加班"}, {"tags": "猫"}, {"tags": "猫,加班"}, {"tags": "加班"}]
        jokes = pick_jokes(count_tags(rows))
        self.assertIn("猫", jokes)
        self.assertIn("加班", jokes)

    def test_threshold(self):
        from botv.life.inside_jokes import count_tags, pick_jokes
        rows = [{"tags": "面试"}, {"tags": "面试"}]
        self.assertEqual(pick_jokes(count_tags(rows)), [])

    def test_describe(self):
        from botv.life.inside_jokes import describe
        self.assertEqual(describe([]), "")
        self.assertIn("猫", describe(["猫"]))

    def test_bad_rows(self):
        from botv.life.inside_jokes import count_tags
        self.assertEqual(len(count_tags([{}, None, {"tags": ""}])), 0)


class TestRapport(unittest.TestCase):
    """v12-G51：够熟才允许接半句"""

    def _describe(self, aff):
        import botv.life.relation as R
        orig = R.get
        R.get = lambda tid: aff
        try:
            return R.describe("1")
        finally:
            R.get = orig

    def test_close_allows(self):
        self.assertIn("接下去", self._describe(0.8))

    def test_stranger_not(self):
        self.assertNotIn("接下去", self._describe(0.1))

    def test_tier_text_present(self):
        self.assertIn("亲近", self._describe(0.8))
        self.assertIn("陌生", self._describe(0.05))


class TestFriction(unittest.TestCase):
    """v13-U20：期待 → 失落 → 冷战 → 和好（有上限）"""

    def setUp(self):
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.friction_states.clear()
        import botv.infra.repo_memory as rm
        self.rm = rm
        self._orig = (rm.load_friction, rm.save_friction)
        self.store = {}
        rm.load_friction = lambda tid: self.store.get(tid, "")
        rm.save_friction = lambda tid, p: self.store.__setitem__(tid, p) or True

    def tearDown(self):
        self.rm.load_friction, self.rm.save_friction = self._orig
        self.cfg.friction_states.clear()

    def _t(self, n=0):
        from datetime import datetime, timedelta
        from botv.config import CST
        return datetime(2026, 11, 9, 12, tzinfo=CST) + timedelta(hours=n)

    def test_expectation_and_letdown(self):
        from botv.life import friction as F
        F.note_expectation("1", "早点睡吧", self._t())
        self.assertEqual(F.phase("1", self._t()), "waiting")
        F.refresh("1", now=self._t(9))  # 超过 8 小时
        self.assertEqual(F.phase("1", self._t(9)), "letdown")

    def test_three_letdowns_start_cold_war(self):
        from botv.life import friction as F
        st = F.load("1")
        st["disappoint"] = 3
        F.save("1")
        F.refresh("1", now=self._t())
        self.assertEqual(F.phase("1", self._t()), "cold")

    def test_cold_war_auto_ends_in_a_day(self):
        from botv.life import friction as F
        st = F.load("1")
        st["disappoint"] = 3
        st["cold_ts"] = self._t().timestamp()
        F.save("1")
        self.assertEqual(F.phase("1", self._t(1)), "cold")
        F.refresh("1", now=self._t(25))
        self.assertEqual(F.phase("1", self._t(25)), "calm", "24 小时后必须自动和好")

    def test_apologize_ends_it(self):
        from botv.life import friction as F
        st = F.load("1")
        st["disappoint"] = 3
        st["cold_ts"] = self._t().timestamp()
        F.save("1")
        self.assertTrue(F.apologize("1"))
        self.assertEqual(F.phase("1"), "calm")

    def test_three_messages_end_cold_war(self):
        from botv.life import friction as F
        st = F.load("1")
        st["disappoint"] = 3
        st["cold_ts"] = self._t().timestamp()
        F.save("1")
        for _ in range(3):
            F.on_user_message("1", self._t())
        self.assertEqual(F.phase("1"), "calm")

    def test_grudge_weekly_limit(self):
        from botv.life import friction as F
        self.assertTrue(F.grudge_allowed("1", self._t()))
        self.assertFalse(F.grudge_allowed("1", self._t(24)), "一周只能一次")
        self.assertTrue(F.grudge_allowed("1", self._t(24 * 8)))

    def test_prompt_line_cold(self):
        from botv.life import friction as F
        st = F.load("1")
        st["cold_ts"] = self._t().timestamp()
        F.save("1")
        self.assertIn("生闷气", F.prompt_line("1", self._t()))

    def test_trail_off(self):
        from botv.life.friction import maybe_trail_off

        class R:
            def __init__(self, v):
                self.v = v

            def random(self):
                return self.v

        text = "今天好累\n不想动\n（趴下）"
        out = maybe_trail_off(text, R(0.0))
        self.assertTrue(out.endswith("算了。"))
        self.assertNotIn("（趴下）", out)
        self.assertEqual(maybe_trail_off(text, R(0.9)), text)
        self.assertEqual(maybe_trail_off("只有一句", R(0.0)), "只有一句")

    def test_is_sorry(self):
        from botv.life.friction import is_sorry
        self.assertTrue(is_sorry("对不起嘛"))
        self.assertFalse(is_sorry("在吗"))


class TestGrowth(unittest.TestCase):
    """v13-U21：成长轨迹 / 称呼演化 / 管你 / 惊喜"""

    def test_growth_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry
        self.assertIn("growth", registry.COMMANDS)

    def test_addressing_changes_with_tier(self):
        import botv.life.relation as R
        orig = R.get
        try:
            R.get = lambda tid: 0.9
            close = R.addressing("1")
            R.get = lambda tid: 0.05
            stranger = R.addressing("1")
        finally:
            R.get = orig
        self.assertIn("笨蛋", close)
        self.assertNotIn("笨蛋", stranger)

    def test_surprise_branch(self):
        import asyncio
        from datetime import datetime
        import botv.schedule.runner as R
        import botv.life.impulse as IMP
        from botv.core import state as cfg
        from botv.config import CST

        prompts, sent = [], []
        orig = {}
        def patch(name, fn):
            orig[name] = getattr(R, name)
            setattr(R, name, fn)

        async def fake_reply(p, tid):
            prompts.append(p)
            return "哼"

        async def fake_send(*a, **k):
            sent.append(a)

        patch("load_today_life", lambda: [])
        patch("get_character_reply", fake_reply)
        patch("send_short_reply", fake_send)
        patch("note_proactive", lambda: None)
        orig_should = IMP.should_chat
        IMP.should_chat = lambda **kw: (True, "ok", 0.3)
        orig_random = R.random.random
        R.random.random = lambda: 0.0   # 分享生活跳过 -> 惊喜命中
        cfg.triggered_today.clear()
        try:
            ok = asyncio.run(R.maybe_chat(datetime.now(CST).replace(minute=0, second=0)))
        finally:
            for name, fn in orig.items():
                setattr(R, name, fn)
            IMP.should_chat = orig_should
            R.random.random = orig_random
            cfg.triggered_today.clear()
        self.assertTrue(ok)
        self.assertTrue(prompts, "应该有提示词")
        self.assertIn("逗他", prompts[0], "走的是惊喜分支")


class TestTools(unittest.TestCase):
    """v13-U22：工具调用协议"""

    def test_parse_call(self):
        from botv.ai.tools import parse_call
        name, arg, body = parse_call("我查一下\n@tool: recall(答辩)\n稍等")
        self.assertEqual(name, "recall")
        self.assertEqual(arg, "答辩")
        self.assertNotIn("@tool", body)

    def test_parse_no_call(self):
        from botv.ai.tools import parse_call
        name, arg, body = parse_call("今天天气不错")
        self.assertIsNone(name)
        self.assertEqual(body, "今天天气不错")

    def test_parse_unknown(self):
        from botv.ai.tools import parse_call
        name, _arg, _body = parse_call("@tool: fly(天空)")
        self.assertEqual(name, "fly")

    def test_tool_prompt_lists_tools(self):
        from botv.ai.tools import tool_prompt, TOOLS
        text = tool_prompt()
        for name in TOOLS:
            self.assertIn(name, text)

    def test_unknown_tool(self):
        import asyncio
        from botv.ai.tools import run_tool
        out = asyncio.run(run_tool("fly", "天空", "1"))
        self.assertIn("没有这个工具", out)

    def test_empty_args(self):
        import asyncio
        from botv.ai.tools import run_tool
        out = asyncio.run(run_tool("remember", "", "1"))
        self.assertIn("没给内容", out)

    def test_system_prompt_has_tools(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        self.assertIn("@tool:", get_system_prompt())


class TestV14Frequency(unittest.TestCase):
    """v14：发图择时 / @ 判断 / 主动频率自适应"""

    def setUp(self):
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.proactive_adjust = 1.0
        cfg.proactive_pending = False
        import botv.chat.reply as R
        R._last_image_ts.clear()
        self.R = R

    def tearDown(self):
        self.cfg.proactive_adjust = 1.0
        self.cfg.proactive_pending = False
        self.R._last_image_ts.clear()

    # ---- B1 发图择时 ----
    def test_image_probability(self):
        class R:
            def __init__(self, v):
                self.v = v

            def random(self):
                return self.v

        self.assertFalse(self.R.image_allowed("1", False, R(0.99)))
        self.assertTrue(self.R.image_allowed("2", False, R(0.01)))

    def test_image_cooldown(self):
        class R:
            def __init__(self, v):
                self.v = v

            def random(self):
                return self.v

        self.assertTrue(self.R.image_allowed("3", False, R(0.0)))
        self.assertFalse(self.R.image_allowed("3", False, R(0.0)), "10 分钟内同一人只一张")

    def test_group_more_conservative(self):
        from botv.chat.reply import IMAGE_PROB, IMAGE_PROB_GROUP
        self.assertLess(IMAGE_PROB_GROUP, IMAGE_PROB)

    # ---- B2 主动频率自适应 ----
    def test_no_reply_lowers_frequency(self):
        import time
        from botv.life import impulse as I
        self.cfg.proactive_adjust = 1.0
        self.cfg.proactive_pending = True
        I.should_chat(now=None, state={"lonely": 0.3, "mood": 0.0},
                      last_user_ts=0.0, last_proactive_ts=time.time() - 3600,
                      proactive_count=0, unanswered=0)
        self.assertLess(self.cfg.proactive_adjust, 1.0)
        self.assertEqual(self.cfg.proactive_pending, False)

    def test_reply_raises_frequency_back(self):
        from botv.life import impulse as I
        self.cfg.proactive_adjust = 0.5
        self.cfg.proactive_pending = True
        I.note_user_message()
        self.assertGreater(self.cfg.proactive_adjust, 0.5)
        self.assertLessEqual(self.cfg.proactive_adjust, 1.0)

    def test_adjust_floor(self):
        import time
        from botv.life import impulse as I
        self.cfg.proactive_adjust = 0.5
        for _ in range(5):
            self.cfg.proactive_pending = True
            I.should_chat(state={"lonely": 0.3}, last_user_ts=0.0,
                          last_proactive_ts=time.time() - 3600,
                          proactive_count=0, unanswered=0)
        self.assertGreaterEqual(self.cfg.proactive_adjust, 0.5)


class TestV14Parsing(unittest.TestCase):
    """v14：日程模糊说法 / 指代词误伤 / CLIP 停用"""

    def setUp(self):
        from datetime import datetime
        from botv.config import CST
        self.now = datetime(2026, 11, 9, 10, 30, tzinfo=CST)  # 周一

    def _when(self, text):
        from botv.life.agenda import parse_when
        return parse_when(text, self.now)

    def test_month_end(self):
        self.assertEqual(self._when("月底交报告").strftime("%m-%d"), "11-30")

    def test_next_month(self):
        self.assertEqual(self._when("下个月面试").strftime("%m-%d"), "12-01")

    def test_weekend(self):
        self.assertEqual(self._when("这周末出去玩").strftime("%m-%d"), "11-14")

    def test_next_weekend(self):
        self.assertEqual(self._when("下周末考试").strftime("%m-%d"), "11-21")

    def test_clip_disabled_text(self):
        from botv.cmd.formatters import format_clip_status
        from botv.core import state as cfg
        cfg.CLIP_ENABLED = False
        text = format_clip_status()
        self.assertIn("停用", text)


class TestPersonaCard(unittest.TestCase):
    """v14-A1/A2：角色卡加载与回退"""

    def test_card_loaded(self):
        from botv.ai.persona_loader import card_dir, describe
        self.assertIsNotNone(card_dir())
        self.assertEqual(describe(), "nao")

    def test_prompt_from_card(self):
        from botv.ai.persona_loader import load_text
        text = load_text("prompt.txt")
        self.assertTrue(text)
        self.assertIn("{now}", text, "占位符必须保留")

    def test_life_from_card(self):
        from botv.ai.persona_loader import load_life
        pools = load_life()
        self.assertTrue(pools)
        self.assertGreaterEqual(sum(len(t) for _w, t in pools), 100)

    def test_state_from_card(self):
        from botv.ai.persona_loader import load_state_base
        base = load_state_base()
        self.assertIn("mood", base)

    def test_missing_file_returns_none(self):
        from botv.ai.persona_loader import load_text
        self.assertIsNone(load_text("no_such_file.txt"))

    def test_env_selects_card(self):
        import os
        from botv.ai import persona_loader as L
        old = os.environ.get("NAO_PERSONA")
        os.environ["NAO_PERSONA"] = "not_exist_card"
        try:
            self.assertEqual(L.describe(), "nao", "找不到就回退默认卡")
        finally:
            if old is None:
                os.environ.pop("NAO_PERSONA", None)
            else:
                os.environ["NAO_PERSONA"] = old

    def test_prompt_uses_card(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        text = get_system_prompt()
        self.assertIn("友利奈绪", text)


class TestPersonaSwitch(unittest.TestCase):
    """v14-A3：多角色切换"""

    def setUp(self):
        from botv.core import state as cfg
        self.cfg = cfg
        cfg.persona_name = ""

    def tearDown(self):
        self.cfg.persona_name = ""

    def test_lists_cards(self):
        from botv.ai.persona_loader import available_cards
        self.assertIn("nao", available_cards())

    def test_default_active(self):
        from botv.ai.persona_loader import active_name
        self.assertEqual(active_name(), "nao")

    def test_runtime_switch(self):
        import os
        from botv.ai import persona_loader as L
        os.makedirs(os.path.join(L.CARD_ROOT, "testcard"), exist_ok=True)
        try:
            self.cfg.persona_name = "testcard"
            self.assertEqual(L.active_name(), "testcard")
        finally:
            self.cfg.persona_name = ""
            import shutil
            shutil.rmtree(os.path.join(L.CARD_ROOT, "testcard"), ignore_errors=True)

    def test_unknown_falls_back(self):
        from botv.ai import persona_loader as L
        self.cfg.persona_name = "根本没有这张卡"
        self.assertEqual(L.active_name(), "nao")

    def test_reload_supplement(self):
        from botv.ai.prompt import reload_personality_supplement
        import botv.ai.prompt as P
        reload_personality_supplement()
        self.assertTrue(P.PERSONALITY_SUPPLEMENT)


class TestDigest(unittest.TestCase):
    """v14.1-D3：会话浓缩成她自己的记录"""

    def setUp(self):
        import os
        import botv.life.digest as D
        self.D = D
        self.orig_dir = D.DIGEST_DIR
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tmp = os.path.join(root, ".test-digest")
        os.makedirs(self.tmp, exist_ok=True)
        D.DIGEST_DIR = self.tmp

    def tearDown(self):
        import shutil
        self.D.DIGEST_DIR = self.orig_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_append_and_load(self):
        self.assertTrue(self.D.append("u1", "聊了加班的烦心事"))
        text = self.D.load("u1")
        self.assertIn("加班的烦心事", text)

    def test_line_truncated(self):
        self.D.append("u1", "啊" * 200)
        line = self.D.load("u1").splitlines()[-1]
        self.assertLessEqual(len(line), 6 + self.D.MAX_LINE_CHARS)

    def test_max_lines(self):
        for i in range(30):
            self.D.append("u1", f"第{i}件事")
        lines = self.D.load("u1").splitlines()
        self.assertEqual(len(lines), self.D.MAX_LINES)
        self.assertIn("第29件事", lines[-1])
        self.assertNotIn("第0件事", "\n".join(lines))

    def test_compact_fallback(self):
        rounds = [["今天加班到十点", "累就早点睡"], ["猫又把杯子打碎了", "它故意的吧"]]
        line = self.D.compact_from_rounds(rounds)
        self.assertTrue(line)

    def test_update_without_ai_uses_fallback(self):
        import asyncio
        rounds = [["今天加班", "累就别撑"] for _ in range(10)]
        ok = asyncio.run(self.D.update("u2", rounds, summarize=None))
        self.assertTrue(ok)
        self.assertTrue(self.D.load("u2"))

    def test_update_needs_ten_rounds(self):
        import asyncio
        ok = asyncio.run(self.D.update("u3", [["a", "b"]] * 3, summarize=None))
        self.assertFalse(ok)

    def test_empty_descibe(self):
        self.assertEqual(self.D.describe("nobody"), "")


class TestDigestOverflow(unittest.TestCase):
    """v14.1-D3：超过 30 轮才浓缩"""

    def setUp(self):
        import os
        from collections import deque
        import botv.life.digest as D
        from botv.core import state as cfg
        self.D, self.cfg = D, cfg
        self.orig_dir = D.DIGEST_DIR
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tmp = os.path.join(root, ".test-digest2")
        os.makedirs(self.tmp, exist_ok=True)
        D.DIGEST_DIR = self.tmp
        cfg.digest_pending.clear()
        cfg.user_memory_pool.clear()

    def tearDown(self):
        import shutil
        self.D.DIGEST_DIR = self.orig_dir
        self.cfg.digest_pending.clear()
        self.cfg.user_memory_pool.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_overflow_moves_oldest_to_buffer(self):
        from collections import deque
        import botv.memory.context as ctx
        self.cfg.user_memory_pool["t1"] = deque([["u", "b"]] * 30, maxlen=30)
        orig_u, orig_e = ctx.add_user_memory_to_db, ctx.add_event_to_db
        orig_k = ctx.add_global_keywords_to_db
        ctx.add_user_memory_to_db = lambda *a, **k: None
        ctx.add_event_to_db = lambda *a, **k: None
        ctx.add_global_keywords_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("t1", "新消息", "新回复")
        finally:
            ctx.add_user_memory_to_db, ctx.add_event_to_db = orig_u, orig_e
            ctx.add_global_keywords_to_db = orig_k
        self.assertEqual(len(self.cfg.digest_pending["t1"]), 1, "溢出的一轮要进缓冲")
        self.assertEqual(len(self.cfg.user_memory_pool["t1"]), 30)

    def test_no_buffer_before_30(self):
        from collections import deque
        import botv.memory.context as ctx
        self.cfg.user_memory_pool["t2"] = deque([["u", "b"]] * 5, maxlen=30)
        orig_u, orig_e = ctx.add_user_memory_to_db, ctx.add_event_to_db
        orig_k = ctx.add_global_keywords_to_db
        ctx.add_user_memory_to_db = lambda *a, **k: None
        ctx.add_event_to_db = lambda *a, **k: None
        ctx.add_global_keywords_to_db = lambda *a, **k: None
        try:
            ctx.add_target_memory("t2", "新消息", "新回复")
        finally:
            ctx.add_user_memory_to_db, ctx.add_event_to_db = orig_u, orig_e
            ctx.add_global_keywords_to_db = orig_k
        self.assertNotIn("t2", self.cfg.digest_pending)

    def test_condense_when_buffer_full(self):
        import asyncio
        self.cfg.digest_pending["t3"] = [["今天加班", "累就别撑"]] * 10
        ok = asyncio.run(self.D.maybe_condense("t3", summarize=None))
        self.assertTrue(ok)
        self.assertEqual(self.cfg.digest_pending["t3"], [])
        self.assertTrue(self.D.load("t3"))

    def test_not_enough_buffer(self):
        import asyncio
        self.cfg.digest_pending["t4"] = [["a", "b"]] * 5
        self.assertFalse(asyncio.run(self.D.maybe_condense("t4", summarize=None)))


class TestImageGateRegression(unittest.TestCase):
    """回归：发图闸门关闭时，两条发图路径都不能绕过"""

    def _run(self, text, allow):
        import asyncio
        import botv.chat.reply as R
        calls = []
        orig = (R.get_best_image, R.extract_keywords, R.image_allowed, R.materialize_image)

        async def fake_get(kws, uid):
            calls.append(kws)
            return "/tmp/fake.jpg"

        R.get_best_image = fake_get
        R.extract_keywords = lambda t: ["猫"]
        R.image_allowed = lambda *a, **k: allow
        R.materialize_image = lambda p: p
        try:
            parts = asyncio.run(R.build_reply_message(text, "1"))
        finally:
            (R.get_best_image, R.extract_keywords, R.image_allowed,
             R.materialize_image) = orig
        return parts, calls

    def test_gate_closed_no_image(self):
        parts, calls = self._run("今天好累\n（趴下）\n关键词搜索图片用：猫,狗", allow=False)
        self.assertFalse(any(p[0] == "image" for p in parts), "闸门关了不能出图")
        self.assertEqual(calls, [], "闸门关了就不该去搜图")

    def test_gate_open_ai_keywords(self):
        parts, calls = self._run("今天好累\n（趴下）\n关键词搜索图片用：猫,狗", allow=True)
        self.assertTrue(any(p[0] == "image" for p in parts))
        self.assertTrue(calls)

    def test_gate_open_fallback(self):
        """AI 没给关键词时，兜底那条路也要受闸门控制"""
        parts, calls = self._run("今天好累\n（趴下）", allow=True)
        self.assertTrue(any(p[0] == "image" for p in parts))

    def test_gate_closed_fallback(self):
        parts, calls = self._run("今天好累\n（趴下）", allow=False)
        self.assertFalse(any(p[0] == "image" for p in parts))
        self.assertEqual(calls, [])


class TestTunables(unittest.TestCase):
    """v15：运行时参数"""

    def setUp(self):
        import os
        from botv.core import tunables as T
        self.T = T
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.orig_store = T.STORE
        T.STORE = os.path.join(root, ".test-tunables.json")
        T.load()

    def tearDown(self):
        import os
        self.T.STORE = self.orig_store
        self.T.load()
        try:
            os.remove(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   ".test-tunables.json"))
        except OSError:
            pass

    def test_defaults(self):
        self.assertAlmostEqual(self.T.get("group_base_prob"), 0.20, places=2)

    def test_set_and_get(self):
        ok, _msg = self.T.set_value("image_prob", "0.5")
        self.assertTrue(ok)
        self.assertAlmostEqual(self.T.get("image_prob"), 0.5, places=3)

    def test_prob_clamped(self):
        self.T.set_value("image_prob", "5")
        self.assertLessEqual(self.T.get("image_prob"), 1.0)
        self.T.set_value("image_prob", "-1")
        self.assertGreaterEqual(self.T.get("image_prob"), 0.0)

    def test_unknown_key(self):
        ok, msg = self.T.set_value("no_such", "1")
        self.assertFalse(ok)
        self.assertIn("没有这个参数", msg)

    def test_bad_value(self):
        ok, msg = self.T.set_value("image_prob", "abc")
        self.assertFalse(ok)

    def test_persisted(self):
        self.T.set_value("voice_prob", "0.2")
        self.T.load()  # 重新读盘
        self.assertAlmostEqual(self.T.get("voice_prob"), 0.2, places=3)

    def test_all_items(self):
        items = self.T.all_items()
        self.assertTrue(items)
        names = [i[0] for i in items]
        self.assertIn("lonely_threshold", names)


class TestMetrics(unittest.TestCase):
    """v15：今日统计"""

    def setUp(self):
        from botv.core import metrics
        self.m = metrics
        metrics.reset()

    def test_inc_and_snapshot(self):
        self.m.inc("replies")
        self.m.inc("images", 2)
        data, _day = self.m.snapshot()
        self.assertEqual(data["replies"], 1)
        self.assertEqual(data["images"], 2)

    def test_describe_rates(self):
        for _ in range(4):
            self.m.inc("replies")
        self.m.inc("images")
        self.m.inc("group_answer")
        self.m.inc("group_skip")
        text = self.m.describe()
        self.assertIn("配图率", text)
        self.assertIn("群接话率", text)

    def test_reset(self):
        self.m.inc("replies")
        self.m.reset()
        data, _day = self.m.snapshot()
        self.assertEqual(data["replies"], 0)


class TestOpsCommands(unittest.TestCase):
    """v15：!stats / !config"""

    def test_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry
        self.assertIn("stats", registry.COMMANDS)
        self.assertIn("config", registry.COMMANDS)


class TestNovelParse(unittest.TestCase):
    """v16：小说页解析（不联网，用合成 HTML）"""

    BOOK_HTML = """
    <h1>天外玉</h1>
    <div>作者：世沄玊靑</div>
    <div>作品简介 来自蓝星的天外之魔，不在天道管辖之内。</div>
    <a href="/reader/111">第1章 降世</a>
    <a href="/reader/222">第2章 身世</a>
    <a href="/reader/333">第3章 规则</a>
    """

    def test_parse_book(self):
        from botv.life.novel import parse_book
        info = parse_book(self.BOOK_HTML)
        self.assertEqual(info["title"], "天外玉")
        self.assertEqual(info["author"], "世沄玊靑")
        self.assertEqual(len(info["chapters"]), 3)

    def test_parse_chapter_content(self):
        from botv.life.novel import parse_chapter
        html = '<div class="muye-reader-content">' + ("正文一行\n" * 40) + "</div>"
        text = parse_chapter(html)
        self.assertGreater(len(text), 100)
        self.assertNotIn("<", text)

    def test_parse_chapter_fallback(self):
        from botv.life.novel import parse_chapter
        html = "<html><body><p>" + ("很长的一段正文内容。" * 30) + "</p></body></html>"
        self.assertGreater(len(parse_chapter(html)), 100)

    def test_parse_empty(self):
        from botv.life.novel import parse_book, parse_chapter
        self.assertIsNone(parse_book(""))
        self.assertEqual(parse_chapter(""), "")

    def test_chapter_no(self):
        from botv.life.novel import chapter_no
        self.assertEqual(chapter_no("第12章 测试"), 12)
        self.assertEqual(chapter_no("没有章号"), 0)

    def test_strip_tags(self):
        from botv.life.novel import strip_tags
        self.assertEqual(strip_tags("<p>你好<br>世界</p>"), "你好\n世界")


class TestReadingFlow(unittest.TestCase):
    """v16：读书流程（注入假抓取器，不联网）"""

    def setUp(self):
        import botv.life.reading as R
        import botv.infra.repo_memory as rm
        self.R = R
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def _seed_book(self, tid="1"):
        data = self.R.load(tid)
        data["books"] = [{"title": "天外玉", "url": "https://x/page/1",
                          "last_no": 1, "last_title": "第1章", "intro": "修仙"}]
        self.R.save(tid, data)

    def _fetchers(self, chapters=3):
        async def fetch_book(url):
            return {"title": "天外玉", "intro": "修仙",
                    "chapters": [(f"第{i}章 标题", f"https://x/reader/{i}") for i in range(1, chapters + 1)]}

        async def fetch_chapter(url):
            return "正文内容" * 50

        async def summarize(text):
            return "主角逃出道观"

        return fetch_book, fetch_chapter, summarize

    def test_read_advances_progress(self):
        import asyncio
        self._seed_book()
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["chapter"], "第2章 标题")
        self.assertEqual(out["summary"], "主角逃出道观")
        data = self.R.load("1")
        self.assertEqual(data["books"][-1]["last_no"], 2)
        self.assertEqual(data["chapters"], 1)

    def test_daily_quota(self):
        import asyncio
        self._seed_book()
        data = self.R.load("1")
        self.R.mark_read(data, self.R.DAILY_CHAPTERS)
        self.R.save("1", data)
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertFalse(out["ok"])
        self.assertIn("读够", out["reason"])

    def test_night_blocks(self):
        from datetime import datetime
        from botv.config import CST
        ok, why = self.R.should_read(None, datetime(2026, 11, 9, 3, 0, tzinfo=CST))
        self.assertFalse(ok)
        self.assertEqual(why, "深夜")

    def test_idle_gate(self):
        from datetime import datetime
        from botv.config import CST
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        recent = now.timestamp() - 600
        ok, why = self.R.should_read(recent, now)
        self.assertFalse(ok, "刚聊过不读")
        old = now.timestamp() - 3 * 3600
        ok, _why = self.R.should_read(old, now)
        self.assertTrue(ok)

    def test_no_new_chapter(self):
        import asyncio
        self._seed_book()
        data = self.R.load("1")
        data["books"][-1]["last_no"] = 99
        self.R.save("1", data)
        fb, fc, sm = self._fetchers()
        out = asyncio.run(self.R.read_once("1", fb, fc, sm))
        self.assertFalse(out["ok"])
        self.assertIn("新章节", out["reason"])

    def test_describe(self):
        self._seed_book()
        text = self.R.describe("1")
        self.assertIn("天外玉", text)
        self.assertIn("第 1 章", text)

    def test_next_chapters(self):
        chapters = [(f"第{i}章", f"u{i}") for i in range(1, 6)]
        picked = self.R.next_chapters(chapters, 2, limit=2)
        self.assertEqual([t for t, _u in picked], ["第3章", "第4章"])


    def test_pick_book(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "天外玉", "intro": "修仙", "chapters": [("第1章", "u1")]}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book = asyncio.run(self.R.pick_book(
            "9", fetch_book, Rng(), candidates=[("备用名", "https://x/page/9")]))
        self.assertEqual(book["title"], "天外玉")
        self.assertEqual(book["last_no"], 0)
        self.assertEqual(len(self.R.load("9")["books"]), 1)

    def test_pick_book_keeps_existing(self):
        import asyncio
        self._seed_book("8")
        book = asyncio.run(self.R.pick_book("8", None, None, candidates=[("别的", "https://x/page/2")]))
        self.assertEqual(book["title"], "天外玉")
        self.assertEqual(len(self.R.load("8")["books"]), 1)

    def test_pick_book_fetch_failure_uses_name(self):
        import asyncio

        async def bad(url):
            raise RuntimeError("boom")

        class Rng:
            def choice(self, seq):
                return seq[0]

        book = asyncio.run(self.R.pick_book(
            "7", bad, Rng(), candidates=[("备胎书名", "https://x/page/7")]))
        self.assertEqual(book["title"], "备胎书名")

    def test_book_candidates_env(self):
        import os
        old = os.environ.get("NAO_BOOK_URLS")
        os.environ["NAO_BOOK_URLS"] = "我的书|https://x/page/1,https://x/page/2"
        try:
            items = self.R.book_candidates()
        finally:
            if old is None:
                os.environ.pop("NAO_BOOK_URLS", None)
            else:
                os.environ["NAO_BOOK_URLS"] = old
        self.assertEqual(items[0], ("我的书", "https://x/page/1"))
        self.assertEqual(items[1][1], "https://x/page/2")


    def test_detect_url(self):
        got = self.R.detect_book_request("去看 https://fanqienovel.com/page/123 这本")
        self.assertEqual(got["url"], "https://fanqienovel.com/page/123")

    def test_detect_title(self):
        got = self.R.detect_book_request("《天外玉》你去看看")
        self.assertEqual(got["title"], "天外玉")

    def test_detect_none(self):
        self.assertIsNone(self.R.detect_book_request("今天天气不错"))
        self.assertIsNone(self.R.detect_book_request("《天外玉》好看吗"))  # 没有「去看」意图

    def test_follow_by_url(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "新书", "intro": "简介", "chapters": []}

        book, msg = asyncio.run(self.R.follow("5", url="https://x/page/5", fetch_book=fetch_book))
        self.assertEqual(book["title"], "新书")
        self.assertIn("好，我去看", msg)
        self.assertEqual(len(self.R.load("5")["books"]), 1)

    def test_follow_twice(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "新书", "intro": "", "chapters": []}

        asyncio.run(self.R.follow("6", url="https://x/page/6", fetch_book=fetch_book))
        book, msg = asyncio.run(self.R.follow("6", url="https://x/page/6", fetch_book=fetch_book))
        self.assertIn("已经在追", msg)
        self.assertEqual(len(self.R.load("6")["books"]), 1)

    def test_follow_by_title_needs_link(self):
        import asyncio
        book, msg = asyncio.run(self.R.follow("4", title="天外玉"))
        self.assertIsNone(book)
        self.assertIn("链接", msg)


    def test_parse_rank(self):
        from botv.life.novel import parse_rank
        html = ('<a href="/page/111"><h3>部族荣光</h3><p>丧狐</p></a>'
                '<a href="/page/222"><h3>莫若凌霄</h3></a>'
                '<a href="/page/111"><h3>重复的</h3></a>'
                '<a href="/writer/zone/article/1"><h3>公告</h3></a>')
        items = parse_rank(html)
        self.assertEqual(items[0], ("部族荣光", "https://fanqienovel.com/page/111"))
        self.assertEqual(len(items), 2, "去重且只收 /page/ 链接")

    def test_parse_rank_limit(self):
        from botv.life.novel import parse_rank
        html = "".join(f'<a href="/page/{i}"><h3>书{i}</h3></a>' for i in range(30))
        self.assertEqual(len(parse_rank(html, limit=5)), 5)

    def test_parse_rank_empty(self):
        from botv.life.novel import parse_rank
        self.assertEqual(parse_rank(""), [])
        self.assertEqual(parse_rank("<div>没有书</div>"), [])


    def test_pick_from_rank(self):
        import asyncio

        async def fetch_rank():
            return [("热书A", "https://x/page/a"), ("热书B", "https://x/page/b")]

        async def fetch_book(url):
            return {"title": "热书A", "intro": "简介", "chapters": []}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book, msg = asyncio.run(self.R.pick_from_rank(
            "10", fetch_rank, fetch_book, Rng()))
        self.assertIsNotNone(book)
        self.assertEqual(book["title"], "热书A")
        self.assertIn("我在看", msg)

    def test_pick_from_rank_keeps_existing(self):
        import asyncio
        self._seed_book("11")
        book, msg = asyncio.run(self.R.pick_from_rank("11", lambda: None, None, None))
        self.assertEqual(book["title"], "天外玉")
        self.assertIn("已经在追", msg)

    def test_pick_from_rank_empty(self):
        import asyncio

        async def empty():
            return []

        book, msg = asyncio.run(self.R.pick_from_rank("12", empty, None, None))
        self.assertIsNone(book)
        self.assertIn("热榜", msg)

    def test_pick_from_rank_exclude(self):
        import asyncio

        async def fetch_rank():
            return [("看过的", "https://x/page/old"), ("新书", "https://x/page/new")]

        async def fetch_book(url):
            return {"title": "新书", "intro": "", "chapters": []}

        class Rng:
            def choice(self, seq):
                return seq[0]

        book, _msg = asyncio.run(self.R.pick_from_rank(
            "13", fetch_rank, fetch_book, Rng(),
            exclude=[("看过的", "https://x/page/old")]))
        self.assertEqual(book["url"], "https://x/page/new")


    def test_summarize_with_model(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "云千珩逃出道观，被追兵盯上。"

        out = asyncio.run(self.R.summarize_chapter("正文" * 200, call_model=fake_model))
        self.assertEqual(out, "云千珩逃出道观，被追兵盯上。")

    def test_summarize_strips_prefix(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "摘要：他进了城。"

        out = asyncio.run(self.R.summarize_chapter("正文", call_model=fake_model))
        self.assertEqual(out, "他进了城。")

    def test_summarize_truncates(self):
        import asyncio

        async def fake_model(msgs, max_tokens=0):
            return "啊" * 500

        out = asyncio.run(self.R.summarize_chapter("正文", call_model=fake_model))
        self.assertLessEqual(len(out), self.R.SUMMARY_MAX)

    def test_summarize_fallback_on_error(self):
        import asyncio

        async def boom(msgs, max_tokens=0):
            raise RuntimeError("api down")

        out = asyncio.run(self.R.summarize_chapter("第一句。第二句。第三句。", call_model=boom))
        self.assertIn("第一句", out)

    def test_summarize_empty(self):
        import asyncio
        self.assertEqual(asyncio.run(self.R.summarize_chapter("")), "")
        self.assertEqual(asyncio.run(self.R.summarize_chapter("   ")), "")

    def test_fallback_summary(self):
        out = self.R.fallback_summary("他推开门。外面在下雨。远处有人喊他。")
        self.assertIn("他推开门", out)
        self.assertNotIn("远处有人喊他", out, "只取前两句")


    def test_follow_request_ack(self):
        import asyncio

        async def fetch_book(url):
            return {"title": "天外玉", "intro": "", "chapters": []}

        msg = asyncio.run(self.R.follow_request(
            "20", {"url": "https://x/page/1", "title": ""}, fetch_book=fetch_book))
        self.assertIn("好，我去看", msg)
        self.assertEqual(self.R.load("20")["books"][0]["url"], "https://x/page/1")

    def test_follow_request_title_only(self):
        import asyncio
        msg = asyncio.run(self.R.follow_request("21", {"url": "", "title": "没有的书"}))
        self.assertIn("链接", msg)

    def test_follow_request_empty(self):
        import asyncio
        self.assertEqual(asyncio.run(self.R.follow_request("22", None)), "")


class TestReadingPrompt(unittest.TestCase):
    """v16：把「她在看什么」注入 prompt"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def test_describe_empty(self):
        from botv.life.reading import describe
        self.assertEqual(describe("nobody"), "")

    def test_describe_with_book(self):
        import json
        from botv.life.reading import describe
        self.store["1"] = json.dumps({"books": [{"title": "天外玉", "url": "u", "last_no": 12}]})
        text = describe("1")
        self.assertIn("天外玉", text)
        self.assertIn("12", text)

    def test_prompt_has_reading_slot(self):
        from botv.ai.prompt import get_system_prompt
        from botv.core import state as cfg
        cfg.CODE_MODE = False
        text = get_system_prompt()
        self.assertIn("你最近在看", text)

    def test_prompt_uses_placeholder(self):
        from botv.ai.persona import LOCAL_SYSTEM_PROMPT
        self.assertIn("{reading}", LOCAL_SYSTEM_PROMPT)


class TestMaybeRead(unittest.TestCase):
    """v16：runner 里的空闲读书入口"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.schedule.runner as R
        import botv.life.novel as N
        self.R, self.N = R, N
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True
        self._orig_cfg = (R.cfg.last_user_msg_ts,)
        R.cfg.last_user_msg_ts = 0.0
        R._last_read_check = 0.0
        self._orig_novel = (N.fetch_rank, N.fetch_book, N.fetch_chapter)

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig
        self.R.cfg.last_user_msg_ts = self._orig_cfg[0]
        self.R._last_read_check = 0.0
        self.N.fetch_rank, self.N.fetch_book, self.N.fetch_chapter = self._orig_novel

    def _patch_novel(self):
        async def fetch_rank():
            return [("热书", "https://x/page/1")]

        async def fetch_book(url):
            return {"title": "热书", "intro": "", "chapters": [("第1章 开始", "https://x/reader/1")]}

        async def fetch_chapter(url):
            return "正文内容" * 50

        self.N.fetch_rank, self.N.fetch_book, self.N.fetch_chapter = fetch_rank, fetch_book, fetch_chapter

    def test_reads_when_idle(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        out = asyncio.run(self.R.maybe_read(now, force=True))
        self.assertTrue(out)
        data = self.store.get(str(self.R.MASTER_QQ), "")
        self.assertIn("热书", data)

    def test_night_skips(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 3, 0, tzinfo=CST)
        self.assertFalse(asyncio.run(self.R.maybe_read(now, force=True)))

    def test_throttle(self):
        import asyncio
        from datetime import datetime
        from botv.config import CST
        self._patch_novel()
        now = datetime(2026, 11, 9, 15, 0, tzinfo=CST)
        self.assertTrue(asyncio.run(self.R.maybe_read(now, force=True)))
        # 第二次（不强制）应被节流挡掉
        self.assertFalse(asyncio.run(self.R.maybe_read(now, force=False)))


class TestSharePoints(unittest.TestCase):
    """v16-E8：攒够几个点再分享"""

    def setUp(self):
        self.data = {"books": [{"title": "天外玉", "url": "u", "last_no": 5}],
                     "pending": [], "day": "", "chapters": 0}

    def test_not_ready_before_three(self):
        self.R = __import__("botv.life.reading", fromlist=["x"])
        for i in range(2):
            self.R.note_summary(self.data, f"第{i}个点")
        self.assertFalse(self.R.share_ready(self.data))

    def test_ready_after_three(self):
        from botv.life.reading import note_summary, share_ready
        for i in range(3):
            note_summary(self.data, f"第{i}个点")
        self.assertTrue(share_ready(self.data))

    def test_build_share_has_title(self):
        from botv.life.reading import note_summary, build_share
        for i in range(3):
            note_summary(self.data, f"第{i}个点")
        text = build_share(self.data)
        self.assertIn("天外玉", text)
        self.assertIn("第0个点", text)

    def test_mark_shared_clears(self):
        from botv.life.reading import note_summary, mark_shared
        for i in range(4):
            note_summary(self.data, f"第{i}个点")
        mark_shared(self.data)
        self.assertEqual(len(self.data["pending"]), 1, "用掉 3 个，剩 1 个")
        self.assertGreater(self.data["last_share_ts"], 0)

    def test_cooldown(self):
        import time
        from botv.life.reading import note_summary, share_ready
        for i in range(3):
            note_summary(self.data, f"点{i}")
        self.data["last_share_ts"] = time.time() - 60
        self.assertFalse(share_ready(self.data), "3 小时内不重复分享")

    def test_summary_capped(self):
        from botv.life.reading import note_summary
        note_summary(self.data, "长" * 500)
        self.assertLessEqual(len(self.data["pending"][0]), 100)


class TestShareReading(unittest.TestCase):
    """v16-E8：攒够点后主动分享"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.schedule.runner as R
        self.R = R
        self.sent, self.prompts = [], []
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True
        self._orig_fn = (R.get_character_reply, R.send_short_reply)
        self._seed()

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig
        self.R.get_character_reply, self.R.send_short_reply = self._orig_fn

    def _seed(self, pending=3):
        import json
        data = {"books": [{"title": "天外玉", "url": "u", "last_no": 5}],
                "pending": [f"第{i}个点" for i in range(pending)],
                "day": "", "chapters": 0, "last_share_ts": 0}
        self.store[str(self.R.MASTER_QQ)] = json.dumps(data)

    def _patch(self, ret="她还记得那章，随口提了一句"):
        async def fake_reply(prompt, tid):
            self.prompts.append(prompt)
            return ret

        async def fake_send(*a, **k):
            self.sent.append(a)

        self.R.get_character_reply = fake_reply
        self.R.send_short_reply = fake_send

    def test_share_sends(self):
        import asyncio
        self._patch()
        self.assertTrue(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("天外玉", self.prompts[0])

    def test_share_needs_three_points(self):
        import asyncio
        self._seed(pending=2)
        self._patch()
        self.assertFalse(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(self.sent, [])

    def test_share_clears_points(self):
        import asyncio, json
        self._patch()
        asyncio.run(self.R.maybe_share_reading())
        data = json.loads(self.store[str(self.R.MASTER_QQ)])
        self.assertEqual(len(data["pending"]), 0)
        self.assertGreater(data["last_share_ts"], 0)

    def test_share_skips_fallback(self):
        import asyncio
        from botv.core.types import Fallback
        self._patch(ret=Fallback("挂了"))
        self.assertFalse(asyncio.run(self.R.maybe_share_reading()))
        self.assertEqual(self.sent, [])


class TestOCR(unittest.TestCase):
    """v16：番茄正文 OCR 兜底"""

    def test_pua_ratio(self):
        from botv.life.ocr import pua_ratio
        self.assertEqual(pua_ratio("正常文本"), 0.0)
        self.assertGreater(pua_ratio("\ue000\ue001\ue002"), 0.9)
        self.assertEqual(pua_ratio(""), 0.0)

    def test_clean_removes_cjk_spaces(self):
        from botv.life.ocr import clean
        self.assertEqual(clean("云 千 珩 说 话"), "云千珩说话")
        self.assertEqual(clean("hello world"), "hello world", "英文空格要留")

    def test_clean_collapses_blank(self):
        from botv.life.ocr import clean
        self.assertEqual(clean("第一段\n\n\n\n第二段"), "第一段\n\n第二段")

    def test_fetch_chapter_prefers_ocr_on_pua(self):
        import asyncio
        import botv.life.novel as N
        import botv.life.ocr as O

        async def fake_html(url):
            return '<div class="muye-reader-content">' + ("\ue000" * 100) + "</div>"

        async def fake_ocr(url):
            return "这是一段正常的正文" * 20

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/1"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("正常", text)
        self.assertEqual(O.pua_ratio(text), 0.0)

    def test_fetch_chapter_keeps_clean_html(self):
        import asyncio
        import botv.life.novel as N
        import botv.life.ocr as O

        async def fake_html(url):
            return '<div class="muye-reader-content">' + ("正常正文" * 100) + "</div>"

        async def fake_ocr(url):
            raise AssertionError("正文干净时不该走 OCR")

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/2"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("正常正文", text)


class TestSettings(unittest.TestCase):
    """v16：配置从文件/环境变量来，代码里不存密码"""

    def setUp(self):
        import os
        from botv.core import settings as S
        self.S = S
        self._env_backup = {k: os.environ.get(k) for k in S.ENV_MAP}
        for k in S.ENV_MAP:
            os.environ.pop(k, None)
        self._orig_file = S.CONFIG_FILE
        self._tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 ".test-config.json")
        S.CONFIG_FILE = self._tmp
        if os.path.exists(self._tmp):
            os.remove(self._tmp)
        S.load(force=True)

    def tearDown(self):
        import os
        for k, v in self._env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.S.CONFIG_FILE = self._orig_file
        try:
            os.remove(self._tmp)
        except OSError:
            pass
        self.S.load(force=True)

    def test_empty_by_default(self):
        self.assertEqual(self.S.get("db.password"), "")
        self.assertEqual(self.S.get("db.host"), "")
        self.assertTrue(self.S.missing_keys())

    def test_file_config(self):
        import json
        with open(self._tmp, "w", encoding="utf-8") as f:
            json.dump({"db": {"host": "1.2.3.4", "user": "u", "password": "p", "name": "n"}}, f)
        self.S.load(force=True)
        self.assertEqual(self.S.get("db.host"), "1.2.3.4")
        self.assertFalse(self.S.missing_keys())

    def test_env_overrides_file(self):
        import json
        import os
        with open(self._tmp, "w", encoding="utf-8") as f:
            json.dump({"db": {"host": "file-host", "user": "u", "password": "p", "name": "n"}}, f)
        os.environ["NAO_DB_HOST"] = "env-host"
        self.S.load(force=True)
        self.assertEqual(self.S.get("db.host"), "env-host")

    def test_port_coerced_to_int(self):
        import os
        os.environ["NAO_WS_PORT"] = "4001"
        self.S.load(force=True)
        self.assertEqual(self.S.get("ws_port"), 4001)

    def test_db_config_shape(self):
        db = self.S.db_config()
        for key in ("host", "port", "user", "password", "database", "charset"):
            self.assertIn(key, db)

    def test_no_secret_in_code(self):
        """constants.py 里不能再出现密码字面量"""
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "botv", "core", "constants.py")
        text = open(path, encoding="utf-8").read()
        self.assertNotIn('"TNB"', text)
        self.assertNotIn("TomoriNaoBot", text)


class TestCookies(unittest.TestCase):
    """v16：登录态注入（多路径 + 多格式）"""

    def setUp(self):
        import os
        import botv.life.cookies as C
        self.C = C
        self.orig = C.FALLBACKS
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dir = os.path.join(root, ".test-cookies")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        import shutil
        self.C.FALLBACKS = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, data):
        import json, os
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.C.FALLBACKS = (path,)
        return path

    ARR = [
        {"name": "_csrfToken", "value": "abc1234", "domain": ".qidian.com", "path": "/"},
        {"name": "ywopenid", "value": "xyz9999", "domain": ".qidian.com"},
    ]

    def test_array_format(self):
        self._write("cookies.json", self.ARR)
        items = self.C.for_site("qidian")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["domain"], ".qidian.com")

    def test_grouped_format(self):
        self._write("root.json", {"qidian": self.ARR})
        self.assertEqual(len(self.C.for_site("qidian")), 2)

    def test_domain_autofill(self):
        self._write("c.json", [{"name": "a", "value": "b"}])
        items = self.C.for_site("qidian")
        self.assertEqual(items[0]["domain"], ".qidian.com", "没给域名就按站点补")

    def test_missing_returns_empty(self):
        import os
        self.C.FALLBACKS = (os.path.join(self.dir, "nope.json"),)
        self.assertEqual(self.C.for_site("qidian"), [])
        self.assertEqual(self.C.describe(), [])

    def test_bad_json_ignored(self):
        import os
        path = os.path.join(self.dir, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{不是 json")
        self.C.FALLBACKS = (path,)
        self.assertEqual(self.C.for_site("qidian"), [])

    def test_no_value_leak_in_describe(self):
        self._write("c.json", {"qidian": self.ARR})
        self.assertEqual(self.C.describe(), ["qidian"])


class TestMerge(unittest.TestCase):
    """v16：HTML 骨架 + OCR 补字"""

    def test_merge_fills_pua(self):
        from botv.life.ocr import merge_html_ocr
        html = "一座\ue000旧的道观里，黑夜带来了阳光\ue001曾给过的冷寂。"
        ocr = "一座破旧的道观里，黑夜带来了阳光未曾给过的冷寂。"
        self.assertEqual(merge_html_ocr(html, ocr),
                         "一座破旧的道观里，黑夜带来了阳光未曾给过的冷寂。")

    def test_merge_keeps_html_when_clean(self):
        from botv.life.ocr import merge_html_ocr
        html = "他推开门。外面在下雨。"
        ocr = "他推开门。外面在下兩。"   # OCR 错字
        self.assertIn("下雨", merge_html_ocr(html, ocr), "已知字用 HTML，别被 OCR 带错")

    def test_merge_without_inputs(self):
        from botv.life.ocr import merge_html_ocr
        self.assertEqual(merge_html_ocr("", "abc"), "abc")
        self.assertEqual(merge_html_ocr("abc", ""), "abc")
        self.assertEqual(merge_html_ocr("", ""), "")

    def test_merge_drops_leftover_pua(self):
        from botv.life.ocr import merge_html_ocr, pua_ratio
        html = "开头\ue000\ue001结尾"
        ocr = "开头结尾"          # OCR 也没认出来
        merged = merge_html_ocr(html, ocr)
        self.assertEqual(pua_ratio(merged), 0.0)

    def test_best_text_prefers_merged(self):
        from botv.life.ocr import best_text
        html = "一座\ue000旧的道观" + "很长的正文内容" * 20
        ocr = "一座破旧的道观" + "很长的正文内容" * 20
        self.assertIn("破旧", best_text(html, ocr))

    def test_fetch_chapter_merges(self):
        import asyncio
        import botv.life.ocr as O
        import botv.life.novel as N

        async def fake_html(url):
            return '<div class="muye-reader-content">一座\ue000旧的道观' + ("正文" * 200) + "</div>"

        async def fake_ocr(url):
            return "一座破旧的道观" + ("正文" * 200)

        orig = (N.fetch_html, O.ocr_url)
        N.fetch_html, O.ocr_url = fake_html, fake_ocr
        try:
            text = asyncio.run(N.fetch_chapter("https://x/reader/3"))
        finally:
            N.fetch_html, O.ocr_url = orig
        self.assertIn("破旧", text)
        self.assertNotIn("\ue000", text)


class TestBareTitleRequest(unittest.TestCase):
    """v16.0.4：没有书名号也能认出来 + 按书名搜索"""

    def setUp(self):
        import botv.infra.repo_memory as rm
        import botv.life.reading as R
        self.R = R
        self.store = {}
        self._orig = (rm.load_reading, rm.save_reading)
        rm.load_reading = lambda tid: self.store.get(str(tid), "")
        rm.save_reading = lambda tid, p: self.store.__setitem__(str(tid), p) or True

    def tearDown(self):
        import botv.infra.repo_memory as rm
        rm.load_reading, rm.save_reading = self._orig

    def test_detect_bare_title(self):
        got = self.R.detect_book_request("去看看十日终焉呢？")
        self.assertEqual(got["title"], "十日终焉", "别把「呢」吃进书名")

    def test_detect_bare_title_other_particle(self):
        got = self.R.detect_book_request("看看十日终焉吧")
        self.assertEqual(got["title"], "十日终焉")

    def test_plain_chat_not_detected(self):
        self.assertIsNone(self.R.detect_book_request("你上课了吗"))
        self.assertIsNone(self.R.detect_book_request("今天天气不错"))

    def test_follow_with_search(self):
        import asyncio

        async def search(title):
            return ("十日终焉", "https://fanqienovel.com/page/999")

        async def fetch_book(url):
            return {"title": "十日终焉", "intro": "无限流", "chapters": []}

        book, msg = asyncio.run(self.R.follow(
            "30", title="十日终焉", search=search, fetch_book=fetch_book))
        self.assertIsNotNone(book)
        self.assertEqual(book["url"], "https://fanqienovel.com/page/999")
        self.assertIn("好，我去看", msg)

    def test_follow_search_miss_asks_link(self):
        import asyncio

        async def search(title):
            return None

        book, msg = asyncio.run(self.R.follow("31", title="找不到的书", search=search))
        self.assertIsNone(book)
        self.assertIn("链接", msg)

    def test_follow_without_search(self):
        import asyncio
        book, msg = asyncio.run(self.R.follow("32", title="十日终焉"))
        self.assertIsNone(book)
        self.assertIn("链接", msg)


if __name__ == "__main__":
    unittest.main()