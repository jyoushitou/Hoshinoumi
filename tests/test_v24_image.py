# ===================== v24.4 ALAPI 空结果防御 =====================
import asyncio
import unittest


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class TestAlapiV244(unittest.TestCase):
    def test_image_urls_empty_and_dict(self):
        from bot.image.fetch import _image_urls
        self.assertEqual(_image_urls(None), [])
        self.assertEqual(_image_urls({}), [])
        self.assertEqual(_image_urls({"url": "u1"}), ["u1"])
        self.assertEqual(_image_urls([{"img": "u2"}, None, "u3"]), ["u2", "u3"])

    def test_empty_response_no_exception(self):
        from bot.image import fetch
        orig = fetch._get

        async def fake(session, url, **kwargs):
            return _Resp({"code": 200, "data": None})

        fetch._get = fake
        try:
            out = asyncio.run(fetch.search_alapi_and_save(["x"]))
            out2 = asyncio.run(fetch.fetch_and_save_acg_image())
        finally:
            fetch._get = orig
        self.assertIsNone(out)
        self.assertIsNone(out2)


if __name__ == "__main__":
    unittest.main()
