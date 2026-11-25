# ===================== 记忆页 API（v35.9.10） =====================
from __future__ import annotations

import json
from collections import Counter

from ..infra import tenant
from .common import json_response

_INTERNAL_KINDS = ("state", "rel", "friction", "reading", "habit", "agenda")


def _uid():
    return str(tenant.owner_id())


def _rows(sql, params):
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute(sql, params)
        return list(c.fetchall() or [])
    finally:
        try: c.close()
        except Exception: pass


def _tags(raw):
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x)]
    try:
        value = json.loads(raw or "[]")
        if isinstance(value, list):
            return [str(x) for x in value if str(x)]
    except Exception:
        pass
    return [x.strip() for x in str(raw or "").replace("，", ",").split(",") if x.strip()]


def _where(extra=""):
    marks = ",".join(["%s"] * len(_INTERNAL_KINDS))
    return f"WHERE user_id=%s AND deleted_at IS NULL AND kind NOT IN ({marks}) {extra}"


def _where_params(*extra):
    return (_uid(), *_INTERNAL_KINDS, *extra)


def build_memory_payload():
    uid = _uid()
    rows = _rows(
        "SELECT id,target_id,kind,summary,tags,source,weight,tier,created_at FROM memories "
        + _where("ORDER BY id DESC LIMIT 200"), _where_params())
    items, events = [], []
    tags = Counter()
    for row in rows:
        item_tags = _tags(row.get("tags"))
        for tag in item_tags:
            tags[tag] += 1
        item = {
            "id": row["id"], "content": row.get("summary") or "",
            "tags": item_tags, "source": str(row.get("source") or "chat"),
            "longterm": bool(float(row.get("weight") or 0) >= 0.7 or row.get("tier") == "long"),
            "created_at": str(row.get("created_at") or ""), "target_id": row.get("target_id") or "",
            "kind": row.get("kind") or "",
        }
        items.append(item)
        events.append({"id": row["id"], "title": item["content"], "kind": item["kind"],
                       "created_at": item["created_at"]})
    from ..infra.repo_profile import build_profile_text
    summary = build_profile_text(uid)
    profile = {"summary": "" if summary == "无" else summary,
               "keywords": [k for k, _ in tags.most_common(12)]}
    target_rows = _rows(
        "SELECT target_id,COUNT(*) AS count FROM memories WHERE user_id=%s AND deleted_at IS NULL "
        "GROUP BY target_id ORDER BY count DESC", (uid,))
    targets = [{"target_id": r["target_id"], "count": int(r["count"] or 0)} for r in target_rows]
    return {
        "total_targets": len(targets), "targets": targets,
        "stats": {"total": len(items), "targets": len(targets),
                  "longterm": sum(1 for x in items if x["longterm"]), "events": len(events)},
        "items": items, "events": events[:50], "profile": profile,
    }


async def handle_item_update(request):
    try:
        item_id = int(request.match_info.get("id", ""))
    except (TypeError, ValueError):
        return json_response({"error": "bad_id"}, 400)
    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "invalid_json"}, 400)
    longterm = bool((body or {}).get("longterm"))
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute(
            "UPDATE memories SET weight=%s, tier=%s WHERE id=%s AND user_id=%s AND deleted_at IS NULL",
            (0.9 if longterm else 0.5, "long" if longterm else "medium", item_id, _uid()))
        c.connection.commit()
        return json_response({"ok": True, "id": item_id, "longterm": longterm})
    finally:
        try: c.close()
        except Exception: pass


async def handle_item_delete(request):
    try:
        item_id = int(request.match_info.get("id", ""))
    except (TypeError, ValueError):
        return json_response({"error": "bad_id"}, 400)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("UPDATE memories SET deleted_at=CURRENT_TIMESTAMP "
                  "WHERE id=%s AND user_id=%s AND deleted_at IS NULL", (item_id, _uid()))
        c.connection.commit()
        return json_response({"ok": True, "id": item_id, "deleted": True})
    finally:
        try: c.close()
        except Exception: pass
