# ===================== v26.7 ingress TCP L4 / worker Unix 帧 =====================
import asyncio
import os
import socket
import tempfile
import unittest

from bot.server import frame, proto_wire as P
from bot.server.tcp_internal import start_unix_frame_server

HAS_UNIX = hasattr(socket, "AF_UNIX") and os.name != "nt"


@unittest.skipUnless(HAS_UNIX, "AF_UNIX unavailable")
class TestIngressTcp(unittest.TestCase):
    def test_worker_unix_ping(self):
        async def run():
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "internal.sock")
                srv = await start_unix_frame_server(path)
                try:
                    r, w = await asyncio.open_unix_connection(path)
                    req = P.InternalRequest("p", "/internal/health", "", "",
                                            P.encode_json_value({}))
                    await frame.write_frame(w, frame.TYPE_REQUEST, P.encode_request(req))
                    t, _f, body = await asyncio.wait_for(frame.read_frame(r), 3)
                    self.assertEqual(P.decode_response(body).status, 200)
                    w.close()
                finally:
                    srv.close()
        asyncio.run(run())

    def test_ingress_l4_proxy(self):
        from bot.ingress import _tcp_proxy
        from bot.core import worker

        async def run():
            with tempfile.TemporaryDirectory() as d:
                old = os.environ.get("NAO_WORKER_SOCKET_DIR")
                os.environ["NAO_WORKER_SOCKET_DIR"] = d
                path = os.path.join(d, "internal.sock")
                upstream = await start_unix_frame_server(path)
                tcp = await asyncio.start_server(_tcp_proxy, "127.0.0.1", 0)
                port = tcp.sockets[0].getsockname()[1]
                try:
                    r, w = await asyncio.open_connection("127.0.0.1", port)
                    await frame.write_frame(w, frame.TYPE_PING, b"")
                    t, _f, _b = await asyncio.wait_for(frame.read_frame(r), 3)
                    self.assertEqual(t, frame.TYPE_RESPONSE)
                    w.close()
                finally:
                    tcp.close()
                    upstream.close()
                    if old is None:
                        os.environ.pop("NAO_WORKER_SOCKET_DIR", None)
                    else:
                        os.environ["NAO_WORKER_SOCKET_DIR"] = old
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
