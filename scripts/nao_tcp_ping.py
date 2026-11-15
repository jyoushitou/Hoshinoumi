# ===================== v26 TCP 探活 =====================
# 用法：python3 scripts/nao_tcp_ping.py [--host 127.0.0.1] [--port 27004]

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.server import frame, proto_wire as P  # noqa: E402


async def main_async(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    req = P.InternalRequest("ping", "/internal/health", "__owner__", "owner",
                            P.encode_json_value({}))
    await frame.write_frame(writer, frame.TYPE_REQUEST, P.encode_request(req))
    t, _f, body = await asyncio.wait_for(frame.read_frame(reader), 5)
    resp = P.decode_response(body)
    print(f"type={t} status={resp.status} body={P.decode_json_value(resp.payload)}")
    writer.close()
    await writer.wait_closed()
    return 0 if resp.status == 200 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=27004)
    args = ap.parse_args()
    return asyncio.run(main_async(args.host, args.port))


if __name__ == "__main__":
    raise SystemExit(main())
