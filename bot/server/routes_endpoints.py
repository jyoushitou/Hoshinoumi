# ===================== Endpoint 注册表 + DeliveryHub API（v35.2.1） =====================
# 注册/列出/停用 endpoint；客户端用 X-Endpoint-Token 拉取并 ack。

import hmac

from ..delivery import hub
from ..infra import repo_delivery, tenant
from .common import json_response


def _owner():
    return tenant.owner_id()


def _endpoint_token(request):
    return (request.headers.get("X-Endpoint-Token") or "").strip()


async def handle_list(request):
    return json_response({"ok": True, "endpoints": repo_delivery.list_endpoints(_owner())})


async def handle_register(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = str((body or {}).get("name") or "").strip()
    kind = str((body or {}).get("kind") or "client").strip()[:32]
    if not name or len(name) > 64:
        return json_response({"ok": False, "error": "bad_name"}, 400)
    try:
        row, token = hub.register(_owner(), name, kind)
    except Exception:
        return json_response({"ok": False, "error": "endpoint_exists"}, 409)
    return json_response({"ok": True, "endpoint": row, "token": token})


async def handle_disable(request):
    try:
        endpoint_id = int(request.match_info.get("id") or 0)
    except ValueError:
        return json_response({"ok": False, "error": "bad_id"}, 400)
    ok = repo_delivery.disable_endpoint(_owner(), endpoint_id)
    return json_response({"ok": ok}, 200 if ok else 404)


def _valid_endpoint(request, endpoint_id):
    row = repo_delivery.endpoint_by_id(_owner(), endpoint_id)
    if not row or not row.get("enabled"):
        return None
    token = _endpoint_token(request)
    if not token:
        return None
    if not hmac.compare_digest(row.get("token_hash", ""), hub.hash_token(token)):
        return None
    return row


async def handle_messages(request):
    try:
        endpoint_id = int(request.match_info.get("id") or 0)
        after_id = int(request.query.get("after_id") or 0)
        limit = int(request.query.get("limit") or 50)
    except ValueError:
        return json_response({"ok": False, "error": "bad_params"}, 400)
    if not _valid_endpoint(request, endpoint_id):
        return json_response({"ok": False, "error": "endpoint_auth_failed"}, 403)
    rows = repo_delivery.pull(_owner(), endpoint_id, after_id=after_id, limit=limit)
    return json_response({"ok": True, "messages": rows})


async def handle_ack(request):
    try:
        endpoint_id = int(request.match_info.get("id") or 0)
    except ValueError:
        return json_response({"ok": False, "error": "bad_id"}, 400)
    if not _valid_endpoint(request, endpoint_id):
        return json_response({"ok": False, "error": "endpoint_auth_failed"}, 403)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    message_id = str((body or {}).get("message_id") or "").strip()
    if not message_id:
        return json_response({"ok": False, "error": "missing_message_id"}, 400)
    ok = repo_delivery.ack(_owner(), endpoint_id, message_id)
    return json_response({"ok": ok})
