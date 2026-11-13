# ===================== v19.5.4 视觉配置：env > config.local.json =====================
import os
import unittest

from tests.test_chat import _stub_missing_deps

_stub_missing_deps()

from botv.ai import vision


class TestVisionConfig(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.pop(k, None) for k in
                     ("NAO_VISION_MODEL", "NAO_VISION_URL", "NAO_VISION_KEY")}
        self._orig_get = None
        from botv.core import settings
        self.settings = settings
        self._orig_get = settings.get

    def tearDown(self):
        for k, v in self._env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        self.settings.get = self._orig_get

    def test_local_file_fallback(self):
        values = {"vision.model": "ep-local", "vision.url": "https://local/v1",
                  "vision.key": "local-key"}
        self.settings.get = lambda path, default=None: values.get(path, default)
        p = vision.providers()
        self.assertTrue(p)
        self.assertEqual(p[0]["model"], "ep-local")
        self.assertEqual(p[0]["url"], "https://local/v1")
        self.assertEqual(p[0]["key"], "local-key")

    def test_env_overrides_file(self):
        self.settings.get = lambda path, default=None: {
            "vision.model": "ep-local", "vision.key": "local-key"}.get(path, default)
        os.environ["NAO_VISION_MODEL"] = "ep-env"
        os.environ["NAO_VISION_KEY"] = "env-key"
        p = vision.providers()
        self.assertEqual(p[0]["model"], "ep-env")
        self.assertEqual(p[0]["key"], "env-key")

    def test_missing_key_skips_provider(self):
        self.settings.get = lambda path, default=None: default
        from botv.core import state as cfg
        old = (cfg.DOUBAO_API_KEY, cfg.DS_API_KEY)
        cfg.DOUBAO_API_KEY = cfg.DS_API_KEY = ""
        try:
            self.assertEqual(vision.providers(), [])
        finally:
            cfg.DOUBAO_API_KEY, cfg.DS_API_KEY = old


if __name__ == "__main__":
    unittest.main()
