# ===================== v35.2.20.0 存钱 API =====================
import sys
import types
import unittest


def _stub_aiohttp():
    try:
        import aiohttp  # noqa: F401
        return
    except ImportError:
        pass
    web = types.ModuleType("aiohttp.web")
    web.json_response = lambda data, status=200, dumps=None: type("R", (), {"text": (dumps or str)(data), "status": status})()
    web.Application = object
    web.middleware = lambda fn: fn
    web.RouteTableDef = lambda: []
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()
from bot.server import routes_savings


class SavingsParseTests(unittest.TestCase):
    def test_cents_and_sign(self):
        self.assertEqual(routes_savings._cents("35.50"), 3550)
        self.assertEqual(routes_savings._cents(35.5), 3550)
        self.assertEqual(routes_savings._signed("expense", 3550), (-3550, "expense"))
        self.assertEqual(routes_savings._signed("income", 8000), (8000, "income"))
        self.assertEqual(routes_savings._signed("saving", 1000), (-1000, "saving"))

    def test_row_and_hash_stable(self):
        row = routes_savings._row({"account": "银行卡", "kind": "expense", "amount": "35.5",
                                   "date": "2026-11-19", "note": "午饭"})
        h1 = routes_savings._hash("__owner__", row)
        h2 = routes_savings._hash("__owner__", dict(row))
        self.assertEqual(h1, h2)
        self.assertLess(row["amount_cents"], 0)

    def test_csv_parse(self):
        body = {"csv": "account,kind,amount,date,note,category\n银行卡,expense,35,2026-11-19,午饭,餐饮\n"}
        rows = routes_savings.parse_rows(body)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["account"], "银行卡")
        self.assertEqual(rows[0]["amount_cents"], -3500)

    def test_invalid_rows(self):
        with self.assertRaises(ValueError):
            routes_savings.parse_rows({"rows": []})
        with self.assertRaises(ValueError):
            routes_savings.parse_rows({"rows": [{"account": "x", "amount": "abc"}]})


if __name__ == "__main__":
    unittest.main()
