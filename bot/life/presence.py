# ===================== 主账号情境（v34.2） =====================

from datetime import datetime, timedelta

ACTIVITIES = {"coding", "meeting", "video", "gaming", "reading",
              "eating", "away", "unknown"}
TTL_MIN = 5


def normalize(activity):
    a = str(activity or "unknown").lower()
    return a if a in ACTIVITIES else "unknown"


def set_presence(user_id, activity, detail="", idle_min=0, source="reporter"):
    from ..infra.conn import get_cursor
    a = normalize(activity)
    detail = (detail or "")[:200]
    c = get_cursor()
    try:
        c.execute("UPDATE owner_presence SET activity=%s, detail=%s, idle_min=%s, "
                  "source=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
                  (a, detail, int(idle_min), source, str(user_id)))
        if not getattr(c, "rowcount", 0):
            c.execute("INSERT INTO owner_presence(user_id,activity,detail,idle_min,source) "
                      "VALUES(%s,%s,%s,%s,%s)",
                      (str(user_id), a, detail, int(idle_min), source))
        c.connection.commit()
        return True
    finally:
        try: c.close()
        except Exception: pass


def get_presence(user_id):
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT * FROM owner_presence WHERE user_id=%s", (str(user_id),))
        row = c.fetchone()
        if not row:
            return None
        try:
            age = datetime.now() - row["updated_at"]
        except Exception:
            age = timedelta(0)
        d = dict(row)
        if age > timedelta(minutes=TTL_MIN):
            d["activity"] = "unknown"
            d["stale"] = True
        return d
    finally:
        try: c.close()
        except Exception: pass


def clear(user_id):
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("DELETE FROM owner_presence WHERE user_id=%s", (str(user_id),))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass


def prompt_block(user_id):
    p = get_presence(user_id)
    if not p or p.get("activity") in (None, "unknown"):
        return ""
    names = {"coding": "写代码", "meeting": "开会", "video": "看视频",
             "gaming": "打游戏", "reading": "看书", "eating": "吃饭",
             "away": "离开"}
    label = names.get(p["activity"], p["activity"])
    idle = p.get("idle_min") or 0
    return f"当前情境：主人在{label}" + (f"，已空闲 {idle} 分钟" if idle else "")
