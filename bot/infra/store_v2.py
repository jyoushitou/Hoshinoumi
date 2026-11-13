# ===================== 新表读取层（v17.4） =====================
# 迁移期间「双读」：先读新表，新表没数据就回退旧表。
# 这样迁移可以分批做，代码随时可回退。
#
#     read_memories("1", limit=10)   # memories → 回退 events
#     read_state("1")                # bot_states → 回退 events(state JSON)
#
# 只读不写——写入仍走旧路径，等 v17.5 再切。

import json

from .conn import get_cursor
from ..log import log_api

MEMORY_KINDS = ("event", "life", "photo")


def read_memories(target_id, limit=20):
    """读记忆：新表 memories 优先，空则回退 events"""
    tid = str(target_id)
    try:
        c = get_cursor()
        c.execute(
            "SELECT summary, tags, importance, created_at, "
            "COALESCE(weight, 0.5) AS weight, COALESCE(tier, 'medium') AS tier "
            "FROM memories "
            "WHERE target_id=%s AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT %s",
            (tid, int(limit)),
        )
        rows = list(c.fetchall())
        if rows:
            log_api(f"[存储] memories 命中 {len(rows)} 条（{tid}）")
            return [_norm(r) for r in rows]
    except Exception as e:
        log_api(f"[存储] memories 读失败，回退 events：{e}")

    return _fallback_events(tid, limit)


def _fallback_events(tid, limit):
    """旧表回退（kind 三类）"""
    try:
        c = get_cursor()
        base = ("SELECT summary, tags, importance, created_at, "
                "0.5 AS weight, 'medium' AS tier FROM memories WHERE target_id=%s ")
        kind = "AND kind IN ('event','life','photo') "
        order = "ORDER BY created_at DESC LIMIT %s"
        try:
            c.execute(base + "AND deleted_at IS NULL " + kind + order,
                      (tid, int(limit)))
        except Exception:
            # 老库没有 deleted_at 列
            c.execute(base + kind + order, (tid, int(limit)))
        rows = list(c.fetchall())
        if rows:
            log_api(f"[存储] 回退 events 读到 {len(rows)} 条（{tid}）")
        return [_norm(r) for r in rows]
    except Exception as e:
        log_api(f"[存储] events 回退也失败：{e}")
        return []


def read_state(target_id):
    """读状态：新表 bot_states 优先，空则回退 events 的 state JSON"""
    tid = str(target_id)
    try:
        c = get_cursor()
        c.execute(
            "SELECT mood, energy, lonely FROM bot_states WHERE target_id=%s", (tid,))
        row = c.fetchone()
        if row:
            return {"mood": float(row["mood"]), "energy": float(row["energy"]),
                    "lonely": float(row["lonely"])}
    except Exception as e:
        log_api(f"[存储] bot_states 读失败，回退 events：{e}")

    # 回退：旧表里的 JSON
    try:
        c = get_cursor()
        c.execute(
            "SELECT event_summary FROM memories WHERE target_id=%s AND kind='state' "
            "ORDER BY id DESC LIMIT 1", (tid,))
        row = c.fetchone()
        if row and (row.get("summary") or row.get("event_summary")):
            data = json.loads((row.get("summary") or row.get("event_summary")))
            if isinstance(data, dict):
                return data
    except Exception as e:
        log_api(f"[存储] state 回退失败：{e}")
    return {}


def _norm(row):
    """统一成 dict，tags 拆成列表"""
    tags = (row.get("tags") or "").strip()
    return {
        "summary": row.get("summary") or "",
        "tags": [t for t in tags.replace("，", ",").split(",") if t] if tags else [],
        "importance": int(row.get("importance") or 3),
        "created_at": row.get("created_at"),
    }


def describe(target_id):
    """给 !stats / !db 用：新表有多少条"""
    tid = str(target_id)
    out = {"memories": 0, "state": False}
    try:
        c = get_cursor()
        c.execute("SELECT COUNT(*) AS n FROM memories WHERE target_id=%s", (tid,))
        out["memories"] = int(c.fetchone()["n"])
        c.execute("SELECT 1 FROM bot_states WHERE target_id=%s", (tid,))
        out["state"] = bool(c.fetchone())
    except Exception:
        pass
    return out
