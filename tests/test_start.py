# ===================== v19.5.7 一键启动 =====================
import os
import unittest

import start


class TestStart(unittest.TestCase):
    def test_api_missing(self):
        from bot.infra import repo_key
        old = repo_key.get_api_key_from_db
        old_env = {k: os.environ.get(k) for k in ("DS_API_KEY", "ARK_API_KEY")}
        repo_key.get_api_key_from_db = lambda name: ""
        for k in old_env:
            os.environ.pop(k, None)
        try:
            self.assertEqual(start._api_missing(), ["DS_API_KEY", "ARK_API_KEY"])
            os.environ["DS_API_KEY"] = "x"
            os.environ["ARK_API_KEY"] = "y"
            self.assertEqual(start._api_missing(), [])
        finally:
            repo_key.get_api_key_from_db = old
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
