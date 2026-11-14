# ===================== v23.5.4 QQ 首次密码 gate =====================
import asyncio
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _stub():
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m


_stub()


class TestQqGate(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema, tenant
        self.tenant = tenant
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "g.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        from scripts import migrate_v23
        migrate_v23.apply(self.c)
        import bot.chat.handler as H
        self.H = H
        self.sent = []
        self.orig_send = H.send_short_reply if hasattr(H, "send_short_reply") else None
        import bot.chat.send as S
        self._orig = S.send_short_reply

        async def fake_send(*args, **kwargs):
            self.sent.append(args[1] if len(args) > 1 else "")

        S.send_short_reply = fake_send
        self._orig_impl = H._handle_message_impl

        async def fake_impl(d, ws):
            return "impl"

        H._handle_message_impl = fake_impl

    def tearDown(self):
        import bot.chat.send as S
        S.send_short_reply = self._orig
        self.H._handle_message_impl = self._orig_impl
        self.tenant.clear_user()
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, text):
        d = {"message_type": "private", "user_id": "987654", "message": text}
        return asyncio.run(self.H._handle_message(d, None))

    def test_first_password_then_chat(self):
        self.assertIsNone(self._run("你好"))
        self.assertIn("设个密码", self.sent[-1])
        self.assertIsNone(self._run("abcdefgh"))
        self.assertIn("密码设好了", self.sent[-1])
        self.assertEqual(self._run("在吗"), "impl")

    def test_short_password_rejected(self):
        self._run("你好")
        self.assertIsNone(self._run("123"))
        self.assertIn("至少 8 位", self.sent[-1])
        self.assertIsNone(self._run("abcdefgh"))


if __name__ == "__main__":
    unittest.main()
