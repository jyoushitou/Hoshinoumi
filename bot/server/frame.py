# ===================== 8+4+body 帧（v26.1） =====================
# 0..3 magic "NAO1"
# 4 version 5 type 6 flags 7 reserved
# 8..11 body length uint32 BE
# 12..  protobuf body

import asyncio
import struct

MAGIC = b"NAO1"
VERSION = 1
TYPE_REQUEST = 1
TYPE_RESPONSE = 2
TYPE_EVENT = 3
TYPE_PING = 4
MAX_BODY = 8 * 1024 * 1024
HEADER = struct.Struct(">4sBBBBI")


def encode_frame(type_, body=b"", flags=0, version=VERSION):
    if len(body) > MAX_BODY:
        raise ValueError("body too large")
    return HEADER.pack(MAGIC, version, int(type_), int(flags), 0, len(body)) + body


def decode_header(raw):
    magic, version, type_, flags, _reserved, length = HEADER.unpack(raw)
    if magic != MAGIC:
        raise ValueError("bad magic")
    if version != VERSION:
        raise ValueError("bad version")
    if length > MAX_BODY:
        raise ValueError("bad length")
    return type_, flags, length


async def read_frame(reader):
    raw = await reader.readexactly(HEADER.size)
    type_, flags, length = decode_header(raw)
    body = await reader.readexactly(length)
    return type_, flags, body


async def write_frame(writer, type_, body=b"", flags=0):
    writer.write(encode_frame(type_, body, flags))
    await writer.drain()


def parse_frames(buffer):
    """同步解析已读缓冲，返回 ([(type,flags,body)], 剩余)。用于测试/粘包。"""
    out = []
    pos = 0
    while len(buffer) - pos >= HEADER.size:
        type_, flags, length = decode_header(buffer[pos:pos + HEADER.size])
        if len(buffer) - pos - HEADER.size < length:
            break
        start = pos + HEADER.size
        out.append((type_, flags, buffer[start:start + length]))
        pos = start + length
    return out, buffer[pos:]
