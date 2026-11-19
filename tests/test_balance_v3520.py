# ===================== v35.2.23.0 API 余额 =====================
import json
import sys
import types
import unittest
from unittest.mock import patch


def _stub_aiohttp():
    try:
        import aiohttp  # noqa: F401
        return
    except ImportError:
        pass
    web = types.ModuleType("aiohttp.web")
    web.json_response = lambda data, status=200, dumps=None: type("R", (), {"text": (dumps or (lambda x: json.dumps(x, ensure_ascii=False)))(data), "status": status})()
    web.Application = object
    web.middleware = lambda fn: fn
    web.RouteTableDef = lambda: []
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()
from bot.core import state as cfg
from bot.server import routes_balance


class _Resp:
    status_code = 200

    def json(self):
        return {"is_available": True, "balance_infos": [{
            "currency": "CNY", "total_balance": "12.34",
            "granted_balance": "2.00", "topped_up_balance": "10.34"}]}


class BalanceTests(unittest.TestCase):
    def test_no_key_is_unknown(self):
        old = cfg.DS_API_KEY
        cfg.DS_API_KEY = ""
        try:
            out = routes_balance._fetch()
            self.assertFalse(out["ok"])
            self.assertEqual(out["error"], "no_key")
        finally:
            cfg.DS_API_KEY = old

    def test_parse_deepseek_balance(self):
        old = cfg.DS_API_KEY
        cfg.DS_API_KEY = "sk-test"
        try:
            with patch("requests.get", return_value=_Resp()):
                out = routes_balance._fetch()
            self.assertTrue(out["ok"])
            self.assertEqual(out["balance_infos"][0]["total_balance"], "12.34")
        finally:
            cfg.DS_API_KEY = old


if __name__ == "__main__":
    unittest.main()
