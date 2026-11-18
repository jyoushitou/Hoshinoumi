# ===================== DeliveryHub（v35.2.1） =====================
# 把同一条消息扇出到该用户的多个客户端 endpoint。
# 只负责排队；客户端用 endpoint token 拉取并 ack。

import hashlib
import json
import secrets
import uuid

from ..infra import repo_delivery


def hash_token(token):
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def issue_token():
    return "nao_ep_" + secrets.token_hex(24)


def register(user_id, name, kind="client"):
    token = issue_token()
    row = repo_delivery.create_endpoint(user_id, name, kind, hash_token(token))
    return row, token


def fanout_text(user_id, target_id, text, channel="private", message_id=None):
    """把一条文本消息排进每个启用 endpoint 的 outbox；返回入队条数。"""
    text = str(text or "").strip()
    if not text:
        return 0
    endpoints = repo_delivery.enabled_endpoints(user_id)
    if not endpoints:
        return 0
    mid = str(message_id or uuid.uuid4().hex)
    payload = json.dumps({
        "message_id": mid,
        "target_id": str(target_id),
        "channel": channel,
        "text": text,
    }, ensure_ascii=False)
    n = 0
    for ep in endpoints:
        n += repo_delivery.enqueue(
            user_id=user_id,
            endpoint_id=int(ep["id"]),
            message_id=mid,
            target_id=str(target_id),
            channel=channel,
            payload_json=payload,
        )
    return n
