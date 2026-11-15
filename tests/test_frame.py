# ===================== v26.1 帧 + protobuf wire =====================
import asyncio
import unittest

from bot.server import frame, proto_wire as P


class TestProtoWire(unittest.TestCase):
    def test_request_roundtrip(self):
        payload = P.encode_json_value({"message": "在吗", "target_id": "1"})
        req = P.InternalRequest("r1", "/internal/chat", "1", "owner", payload)
        got = P.decode_request(P.encode_request(req))
        self.assertEqual(got.request_id, "r1")
        self.assertEqual(got.method, "/internal/chat")
        self.assertEqual(got.user_id, "1")
        self.assertEqual(got.role, "owner")
        self.assertEqual(P.decode_json_value(got.payload)["message"], "在吗")

    def test_response_roundtrip(self):
        resp = P.InternalResponse("r1", 200, "", P.encode_json_value({"ok": True}))
        got = P.decode_response(P.encode_response(resp))
        self.assertEqual(got.status, 200)
        self.assertTrue(P.decode_json_value(got.payload)["ok"])

    def test_field_tags(self):
        body = P.encode_request(P.InternalRequest("x", "m", "u", "owner"))
        self.assertTrue(body.startswith(b"\x0a\x01x"))
        self.assertIn(b"\x12\x01m", body)


class TestFrame(unittest.TestCase):
    def test_header_exact(self):
        raw = frame.encode_frame(frame.TYPE_REQUEST, b"abc")
        self.assertEqual(len(raw), 12 + 3)
        self.assertEqual(raw[:4], b"NAO1")
        self.assertEqual(raw[8:12], b"\x00\x00\x00\x03")

    def test_bad_magic_and_size(self):
        raw = bytearray(frame.encode_frame(frame.TYPE_REQUEST, b"a"))
        raw[0] = ord("X")
        with self.assertRaises(ValueError):
            frame.decode_header(bytes(raw[:12]))
        with self.assertRaises(ValueError):
            frame.decode_header(frame.HEADER.pack(b"NAO1", 1, 1, 0, 0, 0))

    def test_partial_and_coalesced(self):
        a = frame.encode_frame(frame.TYPE_REQUEST, b"a")
        b = frame.encode_frame(frame.TYPE_RESPONSE, b"bb")
        parsed, rest = frame.parse_frames(a[:5])
        self.assertEqual(parsed, [])
        self.assertEqual(rest, a[:5])
        parsed, rest = frame.parse_frames(a + b)
        self.assertEqual([x[2] for x in parsed], [b"a", b"bb"])
        self.assertEqual(rest, b"")

    def test_async_read(self):
        async def run():
            reader = asyncio.StreamReader()
            reader.feed_data(frame.encode_frame(frame.TYPE_REQUEST, b"hello"))
            reader.feed_eof()
            return await frame.read_frame(reader)
        t, _f, body = asyncio.run(run())
        self.assertEqual(t, frame.TYPE_REQUEST)
        self.assertEqual(body, b"hello")

    def test_too_large(self):
        with self.assertRaises(ValueError):
            frame.encode_frame(1, b"x" * (frame.MAX_BODY + 1))


if __name__ == "__main__":
    unittest.main()

