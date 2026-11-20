# ===================== QQ 好友/群目录（v35.5.20） =====================
# 通过 NapCat WebSocket 拉好友和群列表，缓存 60 秒。
# 不使用 mock；连接不可用时返回空，由调用方回退到消息历史。

import time

_CACHE = {"ts": 0.0, "groups": [], "friends": []}
_TTL = 60.0


def _norm_groups(rows):
    out = []
    for x in rows or []:
        try:
            gid = str(x.get("group_id") or "").strip()
            if not gid:
                continue
            out.append({
                "target_id": gid,
                "type": "group",
                "name": str(x.get("group_name") or x.get("name") or gid),
                "member_count": int(x.get("member_count") or 0),
            })
        except Exception:
            continue
    return out


def _norm_friends(rows):
    out = []
    for x in rows or []:
        try:
            uid = str(x.get("user_id") or x.get("uin") or "").strip()
            if not uid:
                continue
            out.append({
                "target_id": uid,
                "type": "private",
                "name": str(x.get("nickname") or x.get("remark") or uid),
                "member_count": 0,
            })
        except Exception:
            continue
    return out


async def directory(force=False):
    now = time.time()
    if not force and now - _CACHE["ts"] < _TTL:
        return {"groups": _CACHE["groups"], "friends": _CACHE["friends"]}
    try:
        from ..chat.send import request_action
        from ..core import state as cfg
        ws = getattr(cfg, "active_ws_qq", None)
        if ws is None:
            return {"groups": [], "friends": []}
        gr = await request_action("get_group_list", {}, ws, "群列表", timeout=3)
        fr = await request_action("get_friend_list", {}, ws, "好友列表", timeout=3)
        groups = _norm_groups((gr or {}).get("data") or [])
        friends = _norm_friends((fr or {}).get("data") or [])
        _CACHE.update({"ts": now, "groups": groups, "friends": friends})
        return {"groups": groups, "friends": friends}
    except Exception:
        return {"groups": _CACHE["groups"], "friends": _CACHE["friends"]}
