# ===================== 自建群聊仓储（v35.9.0.4） =====================
# 本地群，不创建 QQ 群；群消息仍走本地 conversation_messages。
from __future__ import annotations

import json
import uuid

from .conn import get_cursor
from . import tenant


def _uid(value=None):
    return str(value or tenant.owner_id())


def create(user_id, name, members=None):
    uid = _uid(user_id)
    gid = "h_" + uuid.uuid4().hex[:12]
    member_list = [str(x).strip() for x in (members or []) if str(x).strip()][:500]
    c = get_cursor()
    try:
        c.execute(
            "INSERT INTO custom_groups(id,user_id,name,members_json) VALUES(%s,%s,%s,%s)",
            (gid, uid, str(name)[:40], json.dumps(member_list, ensure_ascii=False)),
        )
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return {"id": gid, "name": str(name)[:40], "members": member_list, "member_count": len(member_list)}


def list_for(user_id, limit=100):
    uid = _uid(user_id)
    c = get_cursor()
    try:
        c.execute(
            "SELECT id,name,members_json,created_at FROM custom_groups "
            "WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
            (uid, max(1, min(int(limit or 100), 200))),
        )
        rows = list(c.fetchall() or [])
    finally:
        try: c.close()
        except Exception: pass
    out = []
    for row in rows:
        try: members = json.loads(row.get("members_json") or "[]")
        except Exception: members = []
        out.append({"id": row["id"], "name": row["name"], "members": members,
                    "member_count": len(members), "created_at": str(row.get("created_at") or "")})
    return out
