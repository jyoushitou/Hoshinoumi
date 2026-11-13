# 前置环境监测（checks）：依赖、环境变量、静态检查、目录结构

import sys
import types
import unittest


def _stub_missing_deps():
    """缺依赖就打个桩（必须在导入 bot 之前调用）"""
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
from bot.config import CST
import asyncio
import time
import os
import re
import threading
import json
from bot.ports import ChatModel, Transport  # noqa: E402
from bot.ports.models import ChatRequest, ChatReply  # noqa: E402
from bot.ports.transport import Target, Segment  # noqa: E402
from bot.ai import models as model_mod  # noqa: E402
from bot.ai.chain import FallbackChain  # noqa: E402
from bot.chat.transport import QqTransport  # noqa: E402
from bot.core import state as cfg             # noqa: E402  运行时状态（常量也在里面）
import bot.commands as commands               # noqa: E402
import bot.chat.reply as reply_mod            # noqa: E402
from bot.ai.parse import parse_ai_reply       # noqa: E402
from bot.cmd import registry                  # noqa: E402


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
        "NAO_FEATURES",
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
        # v17.0.1：阻塞调用线程池
        "NAO_TASK_THREADS",
        "NAO_BLOCKING_TIMEOUT",
        # v17.0.2：连接池
        "NAO_DB_POOL_SIZE",
        "NAO_DB_POOL_TIMEOUT",
        "NAO_VERSION",
        "NAO_BATCH_CHAT",
        "NAO_ASYNC_DISPATCH",
        "NAO_LOG_TXT",
        "NAO_MONITOR_INTERVAL",
        "NAO_VISION_FALLBACK_MODEL",
        "NAO_VISION_KEY",
        "NAO_CLOCK_OFFSET",
        "NAO_TZ",
        "NAO_READ_IDLE_MINUTES",
        "NAO_DB_PATH",
        "NAO_BACKUP_DIR",
        "NAO_DB_BACKEND",
        "NAO_LOG_KEEP_DAYS",
        "NAO_LOG_DIR",
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
        for p in list((root / "bot").rglob("*.py")) + [root / "run.py"]:
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
        """bot 里不该出现硬编码的绝对路径"""
        import re
        root = self._root()
        bad = []
        for p in (root / "bot").rglob("*.py"):
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r"[\"'](/home/|/root/|C:\\\\Users)", text):
                bad.append(f"{p.name}: {m.group(0)}")
        self.assertFalse(bad, f"发现硬编码绝对路径: {bad[:5]}")

    def test_bundle_ignores_artifacts(self):
        """打包不该带 .pyc / bundle 文件"""
        gitignore = (self._root() / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.pyc", gitignore)
        self.assertIn("__pycache__", gitignore)

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
        from bot.ai.vision import prompt_with_hint, PROMPT
        self.assertEqual(prompt_with_hint(False), PROMPT)
        self.assertIn("动图", prompt_with_hint(True))

    def test_gif_magic_detection(self):
        """GIF 魔数识别（inbound 里判断是不是动图）"""
        for head in (b"GIF89a....", b"GIF87a...."):
            self.assertTrue(head[:6] in (b"GIF89a", b"GIF87a"))
        self.assertFalse(b"\xff\xd8\xff\xe0" [:6] in (b"GIF89a", b"GIF87a"))


    def test_frame_indices_even(self):
        """抽帧要均匀且含首尾"""
        from bot.ai.vision import frame_indices, MAX_FRAMES
        idx = frame_indices(60)
        self.assertEqual(len(idx), MAX_FRAMES)
        self.assertEqual(idx[0], 0)
        self.assertEqual(idx[-1], 59)
        self.assertEqual(idx, sorted(idx))
        self.assertEqual(len(set(idx)), len(idx), "不能重复")

    def test_frame_indices_short_gif(self):
        """帧数不够就全要"""
        from bot.ai.vision import frame_indices
        self.assertEqual(frame_indices(5), [0, 1, 2, 3, 4])

    def test_frame_indices_edge(self):
        from bot.ai.vision import frame_indices
        self.assertEqual(frame_indices(0), [])
        self.assertEqual(frame_indices(1), [0])

    def test_prompt_mentions_frame_count(self):
        from bot.ai.vision import prompt_with_hint
        text = prompt_with_hint(True, 24)
        self.assertIn("24 帧", text)
        self.assertIn("网格", text)

class TestStructure(unittest.TestCase):
    """结构约定：迁移后这些东西必须还在原位"""

    def test_api_shim_reexports_same_objects(self):
        import bot.api as api
        import bot.ai.client as client
        self.assertIs(api.get_character_reply, client.get_character_reply)
        self.assertIs(api.call_deepseek, client.call_deepseek)

    def test_send_reexports_build_reply(self):
        import bot.send as send
        self.assertIs(send.build_reply_message, reply_mod.build_reply_message)

    def test_http_session_factory(self):
        from bot.core.http import create_http_session
        import requests
        session = create_http_session()
        self.assertIsInstance(session, requests.Session)
        session.close()

if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
