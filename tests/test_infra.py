# 基础设施：线程池、连接池、事件、注册表、版本、配置

import sys
import types
import unittest


def _stub_missing_deps():
    """缺依赖就打个桩（必须在导入 botv 之前调用）"""
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

    try:
        import requests  # noqa: F401
    except ImportError:
        module("requests", Session=lambda: None, get=lambda *a, **k: None,
               post=lambda *a, **k: None)


_stub_missing_deps()


import sys
import types
import unittest
from datetime import datetime
from botv.config import CST
import asyncio
import time
import os
import re
import threading
import json
from botv.ports import ChatModel, Transport  # noqa: E402
from botv.ports.models import ChatRequest, ChatReply  # noqa: E402
from botv.ports.transport import Target, Segment  # noqa: E402
from botv.ai import models as model_mod  # noqa: E402
from botv.ai.chain import FallbackChain  # noqa: E402
from botv.chat.transport import QqTransport  # noqa: E402
from botv.core import state as cfg             # noqa: E402  运行时状态（常量也在里面）
import botv.commands as commands               # noqa: E402
import botv.chat.reply as reply_mod            # noqa: E402
from botv.ai.parse import parse_ai_reply       # noqa: E402
from botv.cmd import registry                  # noqa: E402


class FakeConn:
    """假连接：记录 open/ping 行为"""

    def __init__(self, healthy=True):
        self.open = healthy
        self.pinged = 0
        self.closed = False

    def ping(self, reconnect=False):
        self.pinged += 1
        if not self.open:
            raise RuntimeError("连接已断")

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True
        self.open = False

class FakeCursor:
    def __init__(self, conn):
        self.connection = conn
        self.closed = False

    def close(self):
        self.closed = True

class FakeWS:
    def __init__(self):
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)

    def texts(self):
        """把已发送的报文里的文本段拼出来（命令测试用）"""
        out = []
        for payload in self.sent:
            try:
                d = json.loads(payload)
            except Exception:
                out.append(str(payload))
                continue
            msg = (d.get("params") or {}).get("message") or []
            out.append("".join(
                (seg.get("data") or {}).get("text", "")
                for seg in msg if seg.get("type") == "text"
            ))
        return out

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

class _FakeRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

class _Resp:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "她回了一句"}}]}

class _Session:
    def post(self, *a, **k):
        return _Resp()

def _at(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=CST)

class TestConnPool(unittest.TestCase):
    """连接池：复用、上限、断线重建、借还平衡"""

    def setUp(self):
        from botv.infra.pool import ConnPool

        self.created = []

        def make():
            c = FakeConn()
            self.created.append(c)
            return c

        self.pool = ConnPool(size=2, timeout=0.2, connect=make)

    def test_acquire_creates(self):
        conn = self.pool.acquire()
        self.assertIsNotNone(conn)
        self.assertEqual(len(self.created), 1)

    def test_release_and_reuse(self):
        c1 = self.pool.acquire()
        self.pool.release(c1)
        c2 = self.pool.acquire()
        self.assertIs(c1, c2, "归还后应复用同一条连接")
        self.assertEqual(self.pool.stats()["reused"], 1)

    def test_pool_limit_times_out(self):
        a = self.pool.acquire()
        b = self.pool.acquire()
        with self.assertRaises(TimeoutError):
            self.pool.acquire(timeout=0.1)
        self.pool.release(a)
        self.pool.release(b)
        self.assertEqual(self.pool.stats()["timeouts"], 1)

    def test_broken_connection_recreated(self):
        c1 = self.pool.acquire()
        c1.open = False               # 模拟连接断了
        self.pool.release(c1)         # 归还时应被丢弃
        c2 = self.pool.acquire()      # 再借应该是新连接
        self.assertIsNot(c1, c2)
        self.assertTrue(c2.open)

    def test_borrow_count_balanced(self):
        c1 = self.pool.acquire()
        self.assertEqual(self.pool.stats()["borrowed"], 1)
        self.pool.release(c1)
        self.assertEqual(self.pool.stats()["borrowed"], 0)

    def test_stats_shape(self):
        s = self.pool.stats()
        for key in ("size", "idle", "borrowed", "created", "reused", "timeouts"):
            self.assertIn(key, s)

class TestConnStats(unittest.TestCase):
    """连接池状态只由 pool.py 提供"""

    def setUp(self):
        from botv.infra import pool as P

        self.P = P

        class FakeConn:
            open = True

            def ping(self, reconnect=False):
                pass

            def cursor(self):
                return None

            def close(self):
                pass

        self._orig = P._pool
        P.set_pool(P.ConnPool(size=2, timeout=0.1, connect=lambda: FakeConn()))

    def tearDown(self):
        self.P.set_pool(self._orig)

    def test_conn_stats_fields(self):
        s = self.P.conn_stats()
        for key in ("size", "idle", "borrowed", "reused", "timeouts"):
            self.assertIn(key, s)
        self.assertEqual(s["size"], 2)

    def test_describe_conns(self):
        text = self.P.describe_conns()
        self.assertIn("连接池", text)
        self.assertIn("空闲", text)

class TestDeepseekUsesBlocking(unittest.TestCase):
    """call_deepseek 必须走 run_blocking（统一线程池 + 超时 + 日志）"""

    def test_uses_run_blocking(self):
        import botv.ai.client as C

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()          # 直接在当前线程跑那个同步函数

        orig = (C.run_blocking, C.get_http_session, C.cfg.DS_API_KEY,
                C.save_ai_raw_response)
        C.run_blocking = fake_run_blocking
        C.get_http_session = lambda: _Session()
        C.cfg.DS_API_KEY = "test-key"
        C.save_ai_raw_response = lambda **kw: None
        try:
            out = asyncio.run(C.call_deepseek([{"role": "user", "content": "在吗"}], retry=1))
        finally:
            (C.run_blocking, C.get_http_session, C.cfg.DS_API_KEY,
             C.save_ai_raw_response) = orig

        self.assertEqual(out, "她回了一句")
        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertIn("timeout", calls[0], "必须带超时")
        self.assertEqual(calls[0].get("name"), "deepseek")

class TestDoubaoUsesBlocking(unittest.TestCase):
    """call_doubao 也必须走 run_blocking"""

    def test_uses_run_blocking(self):
        import botv.ai.client as C

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()

        orig = (C.run_blocking, C.get_http_session, C.cfg.DOUBAO_API_KEY,
                C.save_ai_raw_response)
        C.run_blocking = fake_run_blocking
        C.get_http_session = lambda: _Session()
        C.cfg.DOUBAO_API_KEY = "test-key"
        C.save_ai_raw_response = lambda **kw: None
        try:
            out = asyncio.run(C.call_doubao([{"role": "user", "content": "在吗"}]))
        finally:
            (C.run_blocking, C.get_http_session, C.cfg.DOUBAO_API_KEY,
             C.save_ai_raw_response) = orig

        self.assertEqual(out, "她回了一句")
        self.assertEqual(calls[0].get("name"), "doubao")
        self.assertIn("timeout", calls[0])

class TestEvent(unittest.TestCase):
    """Event：去重键、优先级、存活时间、默认值"""

    def _make(self, **kw):
        from botv.events.base import Event

        async def noop():
            return None

        params = {"kind": "idle_read", "key": "book:1", "fn": noop}
        params.update(kw)
        return Event(**params)

    def test_defaults(self):
        from botv.events.base import DEFAULT_TIMEOUT, Priority

        ev = self._make()
        self.assertEqual(ev.priority, Priority.IDLE)
        self.assertEqual(ev.retries, 1)
        self.assertEqual(ev.timeout, DEFAULT_TIMEOUT)
        self.assertTrue(ev.id)

    def test_dedupe_key(self):
        ev = self._make(kind="schedule", key="c1")
        self.assertEqual(ev.dedupe_key(), "schedule:c1")

    def test_ids_unique(self):
        a, b = self._make(), self._make()
        self.assertNotEqual(a.id, b.id)

    def test_age(self):
        ev = self._make()
        later = time.time() + 10
        self.assertGreaterEqual(ev.age(later), 10)

    def test_priority_order(self):
        from botv.events.base import Priority

        self.assertLess(Priority.CHAT, Priority.EVENT)
        self.assertLess(Priority.EVENT, Priority.IDLE)
        self.assertEqual(int(Priority.CHAT), 0)

    def test_fn_callable(self):
        ev = self._make()
        self.assertEqual(asyncio.run(ev.fn()), None)

    def test_str_readable(self):
        ev = self._make(kind="chat", key="822891053")
        text = str(ev)
        self.assertIn("chat:822891053", text)
        self.assertIn("p=2", text)

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

class TestNoRawToThread(unittest.TestCase):
    """除 run_blocking 自身外，代码里不应再有裸的 asyncio.to_thread"""

    ALLOW_FILES = {"blocking.py"}          # 统一入口自己可以调 to_thread

    def test_no_raw_to_thread(self):
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "botv")
        offenders = []
        for base, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(base, name)
                rel = os.path.relpath(path, root)
                text = open(path, encoding="utf-8", errors="ignore").read()
                for i, line in enumerate(text.splitlines(), 1):
                    if "asyncio.to_thread" not in line:
                        continue
                    if line.strip().startswith("#"):
                        continue          # 注释里提到没问题
                    if name in self.ALLOW_FILES:
                        continue
                    offenders.append(f"{rel}:{i} {line.strip()[:60]}")
        self.assertEqual(offenders, [], "还有裸的 to_thread，应改走 run_blocking")

class TestNovelUsesBlocking(unittest.TestCase):
    """fetch_html 必须走 run_blocking（浏览器最慢）"""

    def test_uses_run_blocking(self):
        import botv.life.novel as N

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return "<html>fake</html>"

        orig = N._render
        N._render = lambda url: "<html>fake</html>"
        import botv.infra.blocking as B
        orig_rb = B.run_blocking
        B.run_blocking = fake_run_blocking
        try:
            html = asyncio.run(N.fetch_html("https://x/page/1"))
        finally:
            N._render = orig
            B.run_blocking = orig_rb

        self.assertEqual(html, "<html>fake</html>")
        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertEqual(calls[0].get("name"), "novel")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 30, "浏览器超时要放宽")

class TestOcrUsesBlocking(unittest.TestCase):
    """ocr_url 必须走 run_blocking（截图 + 识别都慢）"""

    def test_uses_run_blocking(self):
        import botv.life.ocr as O
        import botv.infra.blocking as B

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return "识别出来的文字"

        orig = (O._shot_and_ocr, O.tesseract_ok)
        O._shot_and_ocr = lambda url: "识别出来的文字"
        O.tesseract_ok = lambda: True
        orig_rb = B.run_blocking
        B.run_blocking = fake_run_blocking
        try:
            text = asyncio.run(O.ocr_url("https://x/reader/1"))
        finally:
            O._shot_and_ocr, O.tesseract_ok = orig
            B.run_blocking = orig_rb

        self.assertEqual(text, "识别出来的文字")
        self.assertEqual(calls[0].get("name"), "ocr")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 60, "OCR 超时要更宽")

class TestOpsCommands(unittest.TestCase):
    """v15：!stats / !config"""

    def test_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry
        self.assertIn("stats", registry.COMMANDS)
        self.assertIn("config", registry.COMMANDS)

class TestPooledCursor(unittest.TestCase):
    """with pooled_cursor 自动借还（异常也要还）"""

    def setUp(self):
        from botv.infra import pool as P

        self.P = P
        self.created = []

        def make():
            c = FakeConn()
            self.created.append(c)
            return c

        self.orig = P._pool
        P.set_pool(P.ConnPool(size=2, timeout=0.2, connect=make))

    def tearDown(self):
        self.P.set_pool(self.orig)

    def test_auto_release(self):
        from botv.infra.pool import pooled_cursor

        with pooled_cursor() as c:
            self.assertIsNotNone(c)
        self.assertEqual(self.P.get_pool().stats()["borrowed"], 0)

    def test_release_on_exception(self):
        from botv.infra.pool import pooled_cursor

        with self.assertRaises(ValueError):
            with pooled_cursor():
                raise ValueError("boom")
        self.assertEqual(self.P.get_pool().stats()["borrowed"], 0, "异常时也要归还")

class TestRegistry(unittest.TestCase):
    """注册/查询/重复检测/默认参数继承"""

    def setUp(self):
        from botv.events import registry

        registry.clear()
        self.R = registry

    def tearDown(self):
        self.R.clear()

    def test_register_and_get(self):
        Priority = __import__("botv.events.base", fromlist=["Priority"]).Priority

        @self.R.register("idle_read", priority=Priority.IDLE, timeout=180)
        async def handler(ev):
            return "ok"

        h = self.R.get("idle_read")
        self.assertIsNotNone(h)
        self.assertIs(h.fn, handler)
        self.assertEqual(h.timeout, 180)
        self.assertEqual(h.priority, Priority.IDLE)

    def test_duplicate_raises(self):
        @self.R.register("dup")
        async def a(ev):
            return None

        with self.assertRaises(ValueError):
            @self.R.register("dup")
            async def b(ev):
                return None

    def test_require_missing(self):
        with self.assertRaises(KeyError):
            self.R.require("nope")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.R.get("nope"))

    def test_kinds_sorted(self):
        @self.R.register("b")
        async def b(ev):
            return None

        @self.R.register("a")
        async def a(ev):
            return None

        self.assertEqual(self.R.kinds(), ["a", "b"])

    def test_snapshot(self):
        from botv.events.base import Priority

        @self.R.register("chat", priority=Priority.CHAT, description="聊天")
        async def chat(ev):
            return None

        snap = self.R.snapshot()
        self.assertEqual(len(snap), 1)
        self.assertEqual(snap[0]["kind"], "chat")
        self.assertEqual(snap[0]["priority"], 0)
        self.assertEqual(snap[0]["description"], "聊天")

    def test_handler_runs(self):
        @self.R.register("run")
        async def run(ev):
            return 42

        h = self.R.require("run")
        self.assertEqual(asyncio.run(h.fn(None)), 42)

    def test_default_priority_and_timeout(self):
        from botv.events.base import DEFAULT_TIMEOUT, Priority

        @self.R.register("plain")
        async def plain(ev):
            return None

        h = self.R.require("plain")
        self.assertEqual(h.priority, Priority.IDLE)
        self.assertEqual(h.timeout, DEFAULT_TIMEOUT)

class TestRunBlocking(unittest.TestCase):
    """阻塞调用丢线程池：结果正确、异常透传、超时不卡循环、并发真的并行"""

    def test_returns_value(self):
        from botv.infra.blocking import run_blocking

        out = asyncio.run(run_blocking(lambda: 42))
        self.assertEqual(out, 42)

    def test_passes_args_and_kwargs(self):
        from botv.infra.blocking import run_blocking

        def add(a, b=0):
            return a + b

        out = asyncio.run(run_blocking(add, 1, b=2))
        self.assertEqual(out, 3)

    def test_exception_propagates(self):
        from botv.infra.blocking import run_blocking

        def boom():
            raise ValueError("炸了")

        with self.assertRaises(ValueError):
            asyncio.run(run_blocking(boom))

    def test_timeout_raises(self):
        from botv.infra.blocking import run_blocking

        def slow():
            time.sleep(0.5)
            return "done"

        async def main():
            return await run_blocking(slow, timeout=0.05)

        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(main())

    def test_loop_not_blocked(self):
        """阻塞函数执行期间，事件循环还能跑别的协程"""
        from botv.infra.blocking import run_blocking

        ticks = []

        async def ticker():
            for i in range(5):
                ticks.append(i)
                await asyncio.sleep(0.02)

        async def main():
            await asyncio.gather(
                run_blocking(time.sleep, 0.2),
                ticker(),
            )

        asyncio.run(main())
        self.assertEqual(len(ticks), 5, "循环被阻塞时 ticker 跑不完")

    def test_true_parallel(self):
        """两个 0.2 秒的阻塞任务，总耗时应该接近 0.2 而不是 0.4"""
        from botv.infra.blocking import run_blocking

        async def main():
            started = time.time()
            await asyncio.gather(
                run_blocking(time.sleep, 0.2),
                run_blocking(time.sleep, 0.2),
            )
            return time.time() - started

        elapsed = asyncio.run(main())
        self.assertLess(elapsed, 0.36, f"没有并行（用了 {elapsed:.2f}s）")


    def test_shutdown_and_reuse(self):
        """关闭线程池后还能继续用（池会重建）"""
        from botv.infra.blocking import run_blocking, shutdown_pool

        self.assertEqual(asyncio.run(run_blocking(lambda: "before")), "before")
        self.assertTrue(shutdown_pool(wait=True))
        # 关闭后重建，仍能执行
        self.assertEqual(asyncio.run(run_blocking(lambda: "after")), "after")

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

class TestThreadStats(unittest.TestCase):
    """线程池状态只由 blocking.py 提供"""

    def test_thread_stats_shape(self):
        from botv.infra.blocking import thread_stats

        s = thread_stats()
        self.assertIn("size", s)
        self.assertIn("queued", s)
        self.assertEqual(s["size"], 3)

    def test_describe_threads(self):
        from botv.infra.blocking import describe_threads

        text = describe_threads()
        self.assertIn("线程池", text)

    def test_no_conn_leak_into_blocking(self):
        """blocking 模块不该导出连接池相关的名字"""
        import botv.infra.blocking as B

        self.assertFalse(hasattr(B, "pool_stats"))
        self.assertFalse(hasattr(B, "describe_pools"))

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

class TestVersionCommand(unittest.TestCase):
    """!version 注册且能返回内容"""

    def test_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry

        self.assertIn("version", registry.COMMANDS)

    def test_returns_text(self):
        import asyncio

        import botv.commands  # noqa: F401
        from botv.cmd.registry import CommandContext
        from botv.cmd import registry

        cmd = registry.COMMANDS["version"]
        ctx = CommandContext(parts=["version"], uid="1", ws=None, is_group=False, gid=0)
        out = asyncio.run(cmd.handler(ctx))
        self.assertIn("版本", out)

class TestVersionInfo(unittest.TestCase):
    """版本号：来源优先级、格式、运行时长"""

    def setUp(self):
        import os

        from botv.core import version as V

        self.V = V
        self._env = os.environ.pop("NAO_VERSION", None)
        V._cache.clear()

    def tearDown(self):
        import os

        if self._env is not None:
            os.environ["NAO_VERSION"] = self._env
        self.V._cache.clear()

    def test_env_wins(self):
        import os

        os.environ["NAO_VERSION"] = "9.9.9"
        try:
            self.assertEqual(self.V.get_version(force=True), "v9.9.9")
        finally:
            os.environ.pop("NAO_VERSION", None)

    def test_env_with_v_prefix(self):
        import os

        os.environ["NAO_VERSION"] = "v1.2.3"
        try:
            self.assertEqual(self.V.get_version(force=True), "v1.2.3")
        finally:
            os.environ.pop("NAO_VERSION", None)

    def test_fallback_starts_with_v(self):
        ver = self.V.get_version(force=True)
        self.assertTrue(ver.startswith("v"), f"版本号应以 v 开头：{ver}")

    def test_describe_has_fields(self):
        text = self.V.describe()
        self.assertIn("版本", text)
        self.assertIn("已运行", text)
        self.assertIn("Python", text)

    def test_uptime_non_negative(self):
        self.assertGreaterEqual(self.V.uptime_seconds(), 0)

    def test_commit_shape(self):
        commit = self.V.get_commit()
        self.assertTrue(commit == "" or re.fullmatch(r"[0-9a-f]{4,40}", commit), commit)

class TestVisionUsesBlocking(unittest.TestCase):
    """describe_image 必须走 run_blocking（视觉最慢，超时放宽）"""

    def test_uses_run_blocking(self):
        import botv.ai.vision as V

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "描述：一只猫\n标签：猫,窗台"}}]}

        orig = (V.run_blocking, V.prepare, V.cfg.DS_API_KEY)
        V.run_blocking = fake_run_blocking
        V.prepare = lambda img: ("FAKEB64", False, 1)      # 跳过 PIL

        class _FakeRequests:
            Session = lambda self=None: self           # noqa: E731

            def post(self, *a, **k):
                return _Resp()

            def close(self):
                pass

        # vision 是在函数里 import requests 的，改 sys.modules 才能拦到
        import requests as real_requests
        sys.modules["requests"] = _FakeRequests()
        V.cfg.DS_API_KEY = "test-key"
        try:
            out = asyncio.run(V.describe_image(b"fake-image-bytes"))
        finally:
            (V.run_blocking, V.prepare, V.cfg.DS_API_KEY) = orig
            sys.modules["requests"] = real_requests

        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertEqual(calls[0].get("name"), "vision")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 30, "视觉超时要放宽")
        desc, tags = out
        self.assertIn("猫", desc + "".join(tags))

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
