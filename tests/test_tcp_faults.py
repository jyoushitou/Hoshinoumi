# ===================== v26.5 故障注入：坏帧/超长 =====================
import asyncio
import struct
import unittest

from bot.server import frame
from bot.server.tcp_internal import start_tcp_server


async def _expect_closed(port, raw, timeout=2):
    r, w = await asyncio.open_connection("127.0.0.1", port)
    w.write(raw)
    await w.drain()
    data = await asyncio.wait_for(r.read(1), timeout)
    w.close()
    return data == b""


class TestTcpFaults(unittest.TestCase):
    def test_bad_magic_closes(self):
        async def run():
            srv = await start_tcp_server("127.0.0.1", 0)
            port = srv.sockets[0].getsockname()[1]
            try:
                self.assertTrue(await _expect_closed(port, b"BAD!" + b"\x00" * 8))
            finally:
                srv.close()
        asyncio.run(run())

    def test_oversize_header_closes(self):
        async def run():
            srv = await start_tcp_server("127.0.0.1", 0)
            port = srv.sockets[0].getsockname()[1]
            hdr = frame.HEADER.pack(b"NAO1", 1, 1, 0, 0, frame.MAX_BODY + 1)
            try:
                self.assertTrue(await _expect_closed(port, hdr))
            finally:
                srv.close()
        asyncio.run(run())

    def test_reconnect_after_bad_frame(self):
        async def run():
            srv = await start_tcp_server("127.0.0.1", 0)
            port = srv.sockets[0].getsockname()[1]
            try:
                await _expect_closed(port, b"BAD!" + b"\x00" * 8)
                r, w = await asyncio.open_connection("127.0.0.1", port)
                await frame.write_frame(w, frame.TYPE_PING, b"")
                t, _f, _ = await asyncio.wait_for(frame.read_frame(r), 2)
                self.assertEqual(t, frame.TYPE_RESPONSE)
                w.close()
            finally:
                srv.close()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
