# ===================== 出站统一守卫（v17.2 U2） =====================

import os
import re
import unittest


class TestOnlyOutboundSends(unittest.TestCase):
    """除 egress/outbound.py 外，代码里不应再有裸的 ws.send"""

    ALLOW = {"outbound.py"}

    def test_no_raw_ws_send(self):
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "botv")
        offenders = []
        for base, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".py") or name in self.ALLOW:
                    continue
                path = os.path.join(base, name)
                rel = os.path.relpath(path, root)
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if "ws.send(" not in line:
                            continue
                        if line.strip().startswith("#"):
                            continue
                        offenders.append(f"{rel}:{i} {line.strip()[:60]}")
        self.assertEqual(offenders, [], "还有绕过出站口的发送")


class TestSendGoesThroughOutbound(unittest.TestCase):
    """send.py 的发送函数要经过 Outbound"""

    def test_send_or_queue_uses_outbound(self):
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "botv", "chat", "send.py"), encoding="utf-8").read()
        self.assertIn("get_outbound", src)
        self.assertNotIn("async with cfg.send_lock", src)

    def test_flush_uses_outbound(self):
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "botv", "chat", "send.py"), encoding="utf-8").read()
        m = re.search(r"async def flush_outbox\(ws\):(?:.|\n)*?(?=\nasync def |\ndef )", src)
        self.assertIsNotNone(m)
        self.assertIn("out.flush()", m.group(0))


if __name__ == "__main__":
    unittest.main()
