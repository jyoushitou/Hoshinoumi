# ===================== v26.2 TCP 帧服务 =====================
import asyncio
import unittest

from bot.server import frame, proto_wire as P
from bot.server.tcp_internal import start_tcp_server


class TestTcpInternal(unittest.TestCase):
    def test_ping_and_unknown_method(self):
        async def run():
            srv = await start_tcp_server("127.0.0.1", 0)
            port = srv.sockets[0].getsockname()[1]
            try:
                r, w = await asyncio.open_connection("127.0.0.1", port)
                await frame.write_frame(w, frame.TYPE_PING, b"")
                t, _f, _body = await asyncio.wait_for(frame.read_frame(r), 3)
                self.assertEqual(t, frame.TYPE_RESPONSE)
                req = P.InternalRequest("x1", "/nope", "1", "owner",
                                        P.encode_json_value({}))
                await frame.write_frame(w, frame.TYPE_REQUEST, P.encode_request(req))
                t, _f, body = await asyncio.wait_for(frame.read_frame(r), 3)
                resp = P.decode_response(body)
                self.assertEqual(resp.request_id, "x1")
                self.assertEqual(resp.status, 404)
                w.close()
                await w.wait_closed()
            finally:
                srv.close()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

