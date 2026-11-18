# ===================== DSH 只读工具桥（v35.2.0） =====================
# DSH/Qoder 等 IDE 通过本机 HTTP 读取工具清单并调用。
# v35.2.0 只开放只读工具，写操作留到后续版本。

from ..ai.tools import TOOLS, run_tool
from ..infra import tenant
from .common import json_response

# 只读白名单：不开放 remember / agenda_add
READ_ONLY = ("recall", "search_images")


def _tool_list():
    rows = []
    for name in READ_ONLY:
        rows.append({
            "name": name,
            "description": TOOLS.get(name, ""),
            "input": {
                "type": "object",
                "properties": {"arg": {"type": "string"}},
                "required": ["arg"],
            },
            "read_only": True,
        })
    return rows


async def handle_list(request):
    return json_response({
        "ok": True,
        "version": "35.2.0.0",
        "read_only": True,
        "tools": _tool_list(),
    })


async def handle_call(request):
    name = (request.match_info.get("name") or "").strip()
    if name not in READ_ONLY:
        return json_response({
            "ok": False,
            "error": "tool_not_allowed",
            "message": f"{name} 不在只读工具白名单",
        }, 403)

    try:
        body = await request.json()
    except Exception:
        body = {}
    arg = str((body or {}).get("arg") or "").strip()
    if not arg:
        return json_response({
            "ok": False,
            "error": "missing_arg",
            "message": "arg 不能为空",
        }, 400)

    target = tenant.owner_id()
    result = await run_tool(name, arg, target)
    return json_response({
        "ok": True,
        "tool": name,
        "target_id": target,
        "result": result,
    })
