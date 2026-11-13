# ===================== v19.5.5 API 密钥环境变量回退 =====================
import os
import unittest

from tests.test_chat import _stub_missing_deps

_stub_missing_deps()


class TestApiKeyEnv(unittest.TestCase):
    def test_env_used_when_db_empty(self):
        from bot.infra import repo_key
        from bot.core import state as cfg

        old_get = repo_key.get_api_key_from_db
        old_env = {k: os.environ.get(k) for k in ("DS_API_KEY", "ARK_API_KEY", "ALAPI_TOKEN")}
        old_vals = (cfg.DS_API_KEY, cfg.DOUBAO_API_KEY, cfg.STICKER_API_ALAPI_TOKEN)
        repo_key.get_api_key_from_db = lambda name: ""
        os.environ.update({"DS_API_KEY": "d", "ARK_API_KEY": "a", "ALAPI_TOKEN": "l"})
        try:
            repo_key.reload_api_keys()
            self.assertEqual(cfg.DS_API_KEY, "d")
            self.assertEqual(cfg.DOUBAO_API_KEY, "a")
            self.assertEqual(cfg.STICKER_API_ALAPI_TOKEN, "l")
        finally:
            repo_key.get_api_key_from_db = old_get
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            cfg.DS_API_KEY, cfg.DOUBAO_API_KEY, cfg.STICKER_API_ALAPI_TOKEN = old_vals


if __name__ == "__main__":
    unittest.main()
