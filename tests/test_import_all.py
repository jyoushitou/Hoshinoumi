# ===================== v21.9 全模块导入覆盖 =====================
import importlib
import sys
import types
import unittest
from pathlib import Path


def _stub_missing_deps():
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

    for name in ("jieba", "PIL"):
        try:
            __import__(name)
        except ImportError:
            module(name, lcut=lambda s: list(s), Image=None)

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        web = module("aiohttp.web")

        class _Resp:
            def __init__(self, body, status=200, content_type=None):
                self.text = body
                self.body = body.encode("utf-8") if isinstance(body, str) else body
                self.status = status

        def json_response(data, status=200, dumps=None):
            import json
            return _Resp(json.dumps(data, ensure_ascii=False), status)

        web.json_response = json_response
        web.Response = _Resp
        web.middleware = lambda fn: fn
        web.Application = object
        web.RouteTableDef = lambda: []

        aio = module("aiohttp")
        aio.web = web


_stub_missing_deps()


class TestImportAll(unittest.TestCase):
    def test_all_bot_modules_import(self):
        root = Path(__file__).resolve().parents[1]
        modules = set()
        for p in (root / "bot").rglob("*.py"):
            parts = list(p.relative_to(root).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            modules.add(".".join(parts))
        failed = []
        for m in sorted(modules):
            try:
                importlib.import_module(m)
            except Exception as e:
                failed.append(f"{m}: {type(e).__name__}: {e}")
        self.assertEqual(failed, [], "模块导入失败:\n" + "\n".join(failed))


if __name__ == "__main__":
    unittest.main()
