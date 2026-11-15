# ===================== protobuf wire 编解码（v26.1） =====================
# 不依赖 google.protobuf 运行时：只实现本协议用到的 proto3 wire types。
# 消息：
#   InternalRequest  {1 request_id, 2 method, 3 user_id, 4 role, 5 payload}
#   InternalResponse {1 request_id, 2 status, 3 error, 4 payload}
#   StringValue      {1 value}
# payload 是 StringValue 包裹的 JSON，兼容后续换成结构化 message。

import json
import struct
from dataclasses import dataclass

MAX_BODY = 8 * 1024 * 1024


def _varint(n):
    out = bytearray()
    n = int(n)
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _read_varint(data, pos):
    shift = 0
    val = 0
    while True:
        if pos >= len(data):
            raise ValueError("varint truncated")
        b = data[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")


def _field_str(num, value):
    raw = str(value).encode("utf-8")
    return _varint((num << 3) | 2) + _varint(len(raw)) + raw


def _field_bytes(num, raw):
    return _varint((num << 3) | 2) + _varint(len(raw)) + raw


def _field_int(num, value):
    return _varint((num << 3) | 0) + _varint(value)


def _decode_fields(data):
    """返回 {field: [(wire, value)]}；value 对 wire0 是 int，wire2 是 bytes。"""
    out = {}
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        num, wire = tag >> 3, tag & 7
        if wire == 0:
            val, pos = _read_varint(data, pos)
        elif wire == 2:
            ln, pos = _read_varint(data, pos)
            if ln < 0 or pos + ln > len(data):
                raise ValueError("length truncated")
            val = data[pos:pos + ln]
            pos += ln
        elif wire == 1:
            if pos + 8 > len(data):
                raise ValueError("fixed64 truncated")
            val = data[pos:pos + 8]
            pos += 8
        elif wire == 5:
            if pos + 4 > len(data):
                raise ValueError("fixed32 truncated")
            val = data[pos:pos + 4]
            pos += 4
        else:
            raise ValueError(f"unsupported wire {wire}")
        out.setdefault(num, []).append((wire, val))
    return out


def _first_str(fields, num, default=""):
    for wire, val in fields.get(num, []):
        if wire == 2:
            return val.decode("utf-8", "replace")
    return default


def _first_int(fields, num, default=0):
    for wire, val in fields.get(num, []):
        if wire == 0:
            return int(val)
    return default


def _first_bytes(fields, num):
    for wire, val in fields.get(num, []):
        if wire == 2:
            return val
    return b""


@dataclass
class InternalRequest:
    request_id: str = ""
    method: str = ""
    user_id: str = ""
    role: str = ""
    payload: bytes = b""


@dataclass
class InternalResponse:
    request_id: str = ""
    status: int = 200
    error: str = ""
    payload: bytes = b""


def encode_request(r: InternalRequest):
    body = (_field_str(1, r.request_id) + _field_str(2, r.method) +
            _field_str(3, r.user_id) + _field_str(4, r.role) +
            _field_bytes(5, r.payload))
    if len(body) > MAX_BODY:
        raise ValueError("request too large")
    return body


def decode_request(body):
    f = _decode_fields(body)
    return InternalRequest(
        request_id=_first_str(f, 1), method=_first_str(f, 2),
        user_id=_first_str(f, 3), role=_first_str(f, 4),
        payload=_first_bytes(f, 5),
    )


def encode_response(r: InternalResponse):
    body = (_field_str(1, r.request_id) + _field_int(2, r.status) +
            _field_str(3, r.error) + _field_bytes(4, r.payload))
    if len(body) > MAX_BODY:
        raise ValueError("response too large")
    return body


def decode_response(body):
    f = _decode_fields(body)
    return InternalResponse(
        request_id=_first_str(f, 1), status=_first_int(f, 2, 200),
        error=_first_str(f, 3), payload=_first_bytes(f, 4),
    )


def encode_json_value(obj):
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return _field_bytes(1, raw)


def decode_json_value(raw):
    if not raw:
        return {}
    f = _decode_fields(raw)
    text = _first_str(f, 1)
    return json.loads(text) if text else {}
