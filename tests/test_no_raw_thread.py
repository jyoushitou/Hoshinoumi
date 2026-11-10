# ===================== 阻塞调用全覆盖检查（v17.0.3） =====================

import os
import re
import unittest


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


if __name__ == "__main__":
    unittest.main()
