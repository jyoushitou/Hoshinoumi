# ===================== 内部 TCP 帧服务（v35.9.36 typed protobuf） =====================
# 27004 只接受 8+4+body；body 是 typed InternalRequest/InternalResponse。
# 网关路径必须先通过 internal_contracts 的逐接口白名单。
import asyncio
import json
import uuid

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Struct

from ..core import worker
from ..log import log_api, log_system
from . import frame
from . import internal_contracts
from .proto.nao.v1 import internal_v2_pb2 as P

HOST = "127.0.0.1"
MAX_CLIENTS = 64


def _struct_from_json(body):
    data = Struct()
    if isinstance(body, list):
        body = {"data": body}
    if isinstance(body, dict):
        ParseDict(body, data, ignore_unknown_fields=False)
    return data


async def dispatch(req: P.InternalRequest):
    public_path = internal_contracts.resolve(req.path, req.http_method)
    if not public_path:
        return P.InternalResponse(
            request_id=req.request_id, status=404, error="internal_contract_not_found",
            data=_struct_from_json({"ok": False, "error": "internal_contract_not_found"}),
        )
    try:
        params = MessageToDict(req.params) if req.params.ByteSize() else {}
    except Exception:
        params = {}
    query = dict(req.query)
    is_get = str(req.http_method or "POST").upper() == "GET"
    import aiohttp
    from . import config as apicfg

    headers = {"X-User-Id": req.user_id or "__owner__", "X-Role": req.role or "owner"}
    if public_path.startswith("/api/"):
        headers["Authorization"] = "Bearer " + apicfg.API_TOKEN
    import os as _os
    if _os.name == "nt":
        internal_port = int(_os.getenv("NAO_INTERNAL_API_PORT", "27007"))
        connector = aiohttp.TCPConnector(host="127.0.0.1", port=internal_port)
        base_url = f"http://127.0.0.1:{internal_port}"
    else:
        connector = aiohttp.UnixConnector(path=worker.internal_api_socket())
        base_url = "http://internal"
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as s:
            kwargs = {"headers": headers}
            if is_get:
                kwargs["params"] = query or {k: str(v) for k, v in params.items()}
                call = s.get(base_url + public_path, **kwargs)
            else:
                kwargs["json"] = params if isinstance(params, dict) else {}
                call = s.request(str(req.http_method or "POST"), base_url + public_path, **kwargs)
            async with call as r:
                raw = await r.read()
                try:
                    body = json.loads(raw.decode("utf-8"))
                except Exception:
                    body = {"ok": False, "error": raw.decode("utf-8", "replace")[:500]}
                return P.InternalResponse(
                    request_id=req.request_id, status=int(r.status), error="",
                    data=_struct_from_json(body),
                )
    except Exception as e:
        return P.InternalResponse(
            request_id=req.request_id, status=503, error=str(e),
            data=_struct_from_json({"ok": False, "error": str(e)}),
        )


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
                req = P.InternalRequest()
                if not req.ParseFromString(body):
                    raise ValueError("bad InternalRequest")
                if not req.request_id:
                    req.request_id = uuid.uuid4().hex
                resp = await dispatch(req)
                await frame.write_frame(writer, frame.TYPE_RESPONSE, resp.SerializeToString())
            except Exception as e:
                rid = ""
                try:
                    req = P.InternalRequest(); req.ParseFromString(body); rid = req.request_id
                except Exception:
                    pass
                err = P.InternalResponse(
                    request_id=rid, status=400, error=str(e),
                    data=_struct_from_json({"ok": False, "error": str(e)}),
                )
                await frame.write_frame(writer, frame.TYPE_RESPONSE, err.SerializeToString())
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


async def start_unix_frame_server(path):
    """worker 模式：只在 Unix socket 接帧，由 ingress 做 27004 L4 透传。"""
    import os
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass
    server = await asyncio.start_unix_server(handle_client, path,
                                             limit=frame.MAX_BODY + 64)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    log_system(f"[TCP] 内部帧服务已启动: unix:{path}")
    return server
