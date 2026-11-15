# ===================== 内部 TCP 帧服务（v26.2） =====================
# 27004 只接受 8+4+body；业务处理仍复用现有 HTTP handler：
# 通过 data/.../internal-api.sock 转发 JSON，避免重写所有路由。

import asyncio
import json
import uuid

from ..core import worker
from ..log import log_api, log_system
from . import frame
from . import proto_wire as P

HOST = "127.0.0.1"
MAX_CLIENTS = 64


def _status_from_http(code):
    return int(code) if code else 500


async def dispatch(req: P.InternalRequest):
    payload = P.decode_json_value(req.payload)
    method = (req.method or "").strip()
    if "?" in method:
        from urllib.parse import parse_qsl, urlsplit
        _u = urlsplit(method)
        method = _u.path
        for k, v in parse_qsl(_u.query, keep_blank_values=True):
            payload.setdefault(k, v)
    if method == "/internal/health":
        return P.InternalResponse(req.request_id, 200, "",
                                  P.encode_json_value({"ok": True, "status": "ok"}))
    path = method if method.startswith("/internal/") else ""
    if not path:
        return P.InternalResponse(req.request_id, 404, "unknown method",
                                  P.encode_json_value({"ok": False, "error": "unknown method"}))
    import aiohttp

    get_like = path in (
        "/internal/history", "/internal/state", "/internal/cron",
        "/internal/diary", "/internal/shelf", "/internal/auth/owner",
    )
    headers = {"X-User-Id": req.user_id or "__owner__", "X-Role": req.role or "owner"}
    connector = aiohttp.UnixConnector(path=worker.internal_api_socket())
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as s:
            kwargs = {"headers": headers}
            if get_like:
                kwargs["params"] = {k: str(v) for k, v in payload.items()}
                call = s.get("http://internal" + path, **kwargs)
            else:
                kwargs["json"] = payload
                call = s.post("http://internal" + path, **kwargs)
            async with call as r:
                raw = await r.read()
                try:
                    body = json.loads(raw.decode("utf-8"))
                except Exception:
                    body = {"ok": False, "error": raw.decode("utf-8", "replace")[:500]}
                return P.InternalResponse(
                    req.request_id, _status_from_http(r.status), "",
                    P.encode_json_value(body),
                )
    except Exception as e:
        return P.InternalResponse(req.request_id, 503, str(e),
                                  P.encode_json_value({"ok": False, "error": str(e)}))


async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")
    try:
        while True:
            t, _flags, body = await frame.read_frame(reader)
            if t == frame.TYPE_PING:
                await frame.write_frame(writer, frame.TYPE_RESPONSE, b"")
                continue
            if t != frame.TYPE_REQUEST:
                continue
            try:
                req = P.decode_request(body)
                if not req.request_id:
                    req.request_id = uuid.uuid4().hex
                resp = await dispatch(req)
                await frame.write_frame(writer, frame.TYPE_RESPONSE,
                                        P.encode_response(resp))
            except Exception as e:
                rid = ""
                try:
                    rid = P.decode_request(body).request_id
                except Exception:
                    pass
                err = P.InternalResponse(rid, 400, str(e),
                                         P.encode_json_value({"ok": False, "error": str(e)}))
                await frame.write_frame(writer, frame.TYPE_RESPONSE, P.encode_response(err))
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    except Exception as e:
        log_api(f"[TCP] 客户端处理异常 {peer}: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_tcp_server(host=HOST, port=27004):
    server = await asyncio.start_server(handle_client, host, port, limit=frame.MAX_BODY + 64)
    log_system(f"[TCP] 内部帧服务已启动: {host}:{port}")
    return server
