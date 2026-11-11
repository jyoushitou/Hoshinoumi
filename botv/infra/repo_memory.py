# ===================== 记忆仓储 =====================
# 对话记忆 / 全局关键词 / 事件记忆
# 迁移自 db.py（v5-R6），SQL 逐字未改

from collections import deque
from datetime import datetime, timedelta

from ..config import MAX_USER_ROUND, MAX_GLOBAL_KEY, CST
from ..log import log_api, log_err
from .conn import get_cursor
from .dedupe import dedupe_key

# v7-B15：去重窗口与按 kind 的保留上限
DEDUPE_WINDOW_DAYS = 7
KIND_LIMITS = {"life": 60, "event": 30, "promise": 30, "profile": 20, "photo": 40}
KIND_LIMIT_DEFAULT = 20
# 旧代码调 load_events_from_db 时默认只看这几类
DEFAULT_KINDS = ("event", "life", "promise", "photo")


# ===================== 对话记忆 =====================

def load_user_memories_from_db():
    """从数据库加载所有用户的对话记忆"""
    c = get_cursor()
    c.execute("SELECT target_id,user_msg,bot_msg FROM user_memory ORDER BY target_id,id")
    pool = {}
    for r in c.fetchall():
        tid = r["target_id"]
        if tid not in pool:
            pool[tid] = deque(maxlen=MAX_USER_ROUND)  # 每个用户最多保留MAX_USER_ROUND轮对话
        pool[tid].append([r["user_msg"], r["bot_msg"]])
    return pool


def add_user_memory_to_db(tid, user_msg, bot_msg):
    """添加一条对话记忆到数据库，并清理超出轮数的旧记录"""
    c = get_cursor()
    c.execute("INSERT INTO user_memory(target_id,user_msg,bot_msg)VALUES(%s,%s,%s)", (tid, user_msg, bot_msg))
    # 删除超出MAX_USER_ROUND的旧记录
    c.execute("DELETE FROM user_memory WHERE id NOT IN(SELECT id FROM(SELECT id FROM user_memory WHERE target_id=%s ORDER BY id DESC LIMIT %s)AS tmp)AND target_id=%s", (tid, MAX_USER_ROUND, tid))
    c.connection.commit()


# ===================== 全局关键词 =====================

def load_keywords_from_db(target_id=None):
    """加载关键词（v8-B12：按对象分开）

    target_id=None → 返回 {target_id: set}；否则返回该对象的 set
    """
    c = get_cursor()
    if target_id is None:
        c.execute("SELECT target_id, keyword FROM global_keywords ORDER BY id")
        out = {}
        for r in c.fetchall():
            out.setdefault(r["target_id"], set()).add(r["keyword"])
        return out
    c.execute("SELECT keyword FROM global_keywords WHERE target_id=%s ORDER BY id", (target_id,))
    return set(r["keyword"] for r in c.fetchall())


def load_global_keywords_from_db(target_id=""):
    """兼容旧调用：默认取公共库（target_id=""）"""
    return load_keywords_from_db(target_id)


def add_global_keywords_to_db(kws, target_id=""):
    """按对象加关键词，每个对象最多 MAX_GLOBAL_KEY 个"""
    c = get_cursor()
    for kw in kws:
        c.execute("INSERT IGNORE INTO global_keywords(target_id, keyword) VALUES(%s,%s)", (target_id, kw))
    c.execute("SELECT COUNT(*) AS cnt FROM global_keywords WHERE target_id=%s", (target_id,))
    if (c.fetchone()["cnt"] or 0) > MAX_GLOBAL_KEY:
        c.execute("""
            DELETE FROM global_keywords
            WHERE target_id=%s AND id NOT IN(
                SELECT id FROM(SELECT id FROM global_keywords WHERE target_id=%s ORDER BY id DESC LIMIT %s) AS tmp
            )
        """, (target_id, target_id, MAX_GLOBAL_KEY))
    c.connection.commit()


# ===================== 事件记忆 =====================

def load_events_from_db(tid, tag_keywords=None, limit=5, kinds=None):
    """加载记忆，可按标签或 kind 过滤（默认排除 profile）

    v7-B8：多了 kind 维度；旧数据 kind 默认 'event'，兼容。
    """
    c = get_cursor()
    kinds = tuple(kinds) if kinds is not None else DEFAULT_KINDS
    kind_ph = ",".join(["%s"] * len(kinds))
    params = [tid] + list(kinds)

    # v17.4：先读新表 memories；空则回退 events
    try:
        new_sql = ("SELECT summary AS event_summary, tags FROM memories "
                   "WHERE target_id=%s AND deleted_at IS NULL ")
        if tag_keywords:
            conds = " OR ".join(["tags LIKE %s" for _ in tag_keywords[:3]])
            c.execute(new_sql + f"AND ({conds}) ORDER BY id DESC LIMIT %s",
                      [tid] + [f"%{kw}%" for kw in tag_keywords[:3]] + [int(limit)])
        else:
            c.execute(new_sql + "ORDER BY id DESC LIMIT %s", [tid, int(limit)])
        rows = [(r["event_summary"], r["tags"]) for r in c.fetchall()]
        if rows:
            return rows
    except Exception:
        pass      # 新表没建/没数据 → 走旧表

    if tag_keywords:
        conds = " OR ".join(["tags LIKE %s" for _ in tag_keywords[:3]])  # 动态构建LIKE条件
        sql = (f"SELECT event_summary, tags FROM events "
               f"WHERE target_id=%s AND kind IN ({kind_ph}) AND ({conds}) "
               f"ORDER BY id DESC LIMIT %s")
        c.execute(sql, params + [f"%{kw}%" for kw in tag_keywords[:3]] + [limit])
    else:
        sql = (f"SELECT event_summary, tags FROM events "
               f"WHERE target_id=%s AND kind IN ({kind_ph}) "
               f"ORDER BY id DESC LIMIT %s")
        c.execute(sql, params + [limit])
    return [(r["event_summary"], r["tags"]) for r in c.fetchall()]


# ===================== 机器人自身状态（v9-U4） =====================
STATE_TARGET = "__self__"  # 状态行用固定 target，不占任何人的记忆


def load_state_json(target=None):
    """读某个对象的状态；不传就是机器人自己（v14.1-D1 按人分开）

    v17.4：先读新表 bot_states；没有就回退 events 的 JSON。
    新表只有 mood/energy/lonely 三列，其它字段以旧表 JSON 为底合并。
    """
    tid = str(target) if target else STATE_TARGET

    # 旧表（作为底，保留新表没有的字段）
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events WHERE target_id=%s AND kind='state' ORDER BY id DESC LIMIT 1",
        (tid,),
    )
    row = c.fetchone()
    legacy = (row["event_summary"] or "") if row else ""

    # 新表
    try:
        from .store_v2 import read_state
        fresh = read_state(tid)
    except Exception:
        fresh = {}

    if not fresh:
        return legacy
    if not legacy:
        import json
        return json.dumps(fresh, ensure_ascii=False)
    try:
        import json
        data = json.loads(legacy)
        if not isinstance(data, dict):
            data = {}
        data.update(fresh)
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return legacy


def save_state_json(payload, target=None):
    """覆盖写某个对象的状态（一人一行）"""
    tid = str(target) if target else STATE_TARGET
    c = get_cursor()
    c.execute("DELETE FROM events WHERE target_id=%s AND kind='state'", (tid,))
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,'','state',%s,NOW())",
        (tid, payload, dedupe_key(tid, "state", "bot_state")),
    )
    c.connection.commit()
    dual_write("state", tid, payload)

def load_todo_items():
    """所有日程（v10-U10）"""
    c = get_cursor()
    c.execute("SELECT id, event_summary FROM events WHERE target_id=%s AND kind='todo' ORDER BY id",
              (STATE_TARGET,))
    return list(c.fetchall())


def update_todo_item(item_id, payload):
    c = get_cursor()
    c.execute("UPDATE events SET event_summary=%s WHERE id=%s AND kind='todo'", (payload, item_id))
    c.connection.commit()


def delete_todo_item(item_id):
    c = get_cursor()
    c.execute("DELETE FROM events WHERE id=%s AND kind='todo'", (item_id,))
    c.connection.commit()


def load_old_events(tid, days=7, limit=5):
    """取一周以前的旧事（v12-G52 旧事重提）"""
    c = get_cursor()
    c.execute("""
        SELECT event_summary AS summary, DATE(COALESCE(last_seen, created_at)) AS day
        FROM events
        WHERE target_id IN (%s, %s) AND kind IN ('event','life')
          AND COALESCE(last_seen, created_at) < NOW() - INTERVAL %s DAY
        ORDER BY RAND() LIMIT %s
    """, (str(tid), STATE_TARGET, days, limit))
    return list(c.fetchall())


def load_friction(tid):
    """读摩擦状态（v13-U20）"""
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events WHERE target_id=%s AND kind='friction' ORDER BY id DESC LIMIT 1",
        (str(tid),),
    )
    row = c.fetchone()
    legacy = (row["event_summary"] or "") if row else ""

    try:
        c.execute(
            "SELECT expect_ts, expect_text, disappoint, cold_ts, last_grudge "
            "FROM friction_states WHERE target_id=%s", (str(tid),))
        fs = c.fetchone()
    except Exception:
        fs = None
    if not fs:
        return legacy
    fresh = {k: fs[k] for k in ("expect_ts", "expect_text", "disappoint",
                                "cold_ts", "last_grudge") if fs.get(k) is not None}
    if not legacy:
        import json
        return json.dumps({k: str(v) for k, v in fresh.items()}, ensure_ascii=False)
    try:
        import json
        data = json.loads(legacy)
        if not isinstance(data, dict):
            data = {}
        data.update({k: str(v) for k, v in fresh.items()})
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return legacy


def save_friction(tid, payload):
    """覆盖写摩擦状态"""
    c = get_cursor()
    c.execute("DELETE FROM events WHERE target_id=%s AND kind='friction'", (str(tid),))
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,'','friction',%s,NOW())",
        (str(tid), payload, dedupe_key(str(tid), "friction", "friction")),
    )
    c.connection.commit()
    dual_write("friction", tid, payload)

def load_reading(tid):
    """读小说进度（v16）"""
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events WHERE target_id=%s AND kind='reading' ORDER BY id DESC LIMIT 1",
        (str(tid),),
    )
    row = c.fetchone()
    legacy = (row["event_summary"] or "") if row else ""

    try:
        c.execute(
            "SELECT title, intro, last_no, last_chapter FROM reading_progress "
            "WHERE target_id=%s ORDER BY updated_at DESC LIMIT 1", (str(tid),))
        rp = c.fetchone()
    except Exception:
        rp = None
    if not rp:
        return legacy
    fresh = {k: rp[k] for k in ("title", "intro", "last_no", "last_chapter")
             if rp.get(k) is not None}
    if not legacy:
        import json
        return json.dumps(fresh, ensure_ascii=False)
    try:
        import json
        data = json.loads(legacy)
        if not isinstance(data, dict):
            data = {}
        data.update(fresh)
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return legacy


def save_reading(tid, payload):
    """覆盖写小说进度"""
    c = get_cursor()
    c.execute("DELETE FROM events WHERE target_id=%s AND kind='reading'", (str(tid),))
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,'','reading',%s,NOW())",
        (str(tid), payload, dedupe_key(str(tid), "reading", "reading")),
    )
    c.connection.commit()
    dual_write("reading", tid, payload)

def load_habit(tid):
    """读某人的口头禅计数（v12-A17）"""
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events WHERE target_id=%s AND kind='habit' ORDER BY id DESC LIMIT 1",
        (str(tid),),
    )
    row = c.fetchone()
    legacy = (row["event_summary"] or "") if row else ""

    try:
        c.execute(
            "SELECT phrase, count FROM habits WHERE target_id=%s "
            "ORDER BY count DESC LIMIT 5", (str(tid),))
        hs = list(c.fetchall())
    except Exception:
        hs = []
    if not hs:
        return legacy
    fresh = {"phrases": [h["phrase"] for h in hs if h.get("phrase")]}
    if not legacy:
        import json
        return json.dumps(fresh, ensure_ascii=False)
    try:
        import json
        data = json.loads(legacy)
        if not isinstance(data, dict):
            data = {}
        data.update(fresh)
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return legacy


def save_habit(tid, payload):
    """覆盖写口头禅计数（一人一行）"""
    c = get_cursor()
    c.execute("DELETE FROM events WHERE target_id=%s AND kind='habit'", (str(tid),))
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,'','habit',%s,NOW())",
        (str(tid), payload, dedupe_key(str(tid), "habit", "habit")),
    )
    c.connection.commit()


def load_relation(tid):
    """读某人的亲密度（v10-U8）

    v17.4：先读新表 relations；没有就回退 events 的 rel JSON。
    新表只有 affinity/since/tier，其它字段以旧 JSON 为底合并。
    """
    tid = str(tid)
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events WHERE target_id=%s AND kind='rel' ORDER BY id DESC LIMIT 1",
        (tid,),
    )
    row = c.fetchone()
    legacy = (row["event_summary"] or "") if row else ""

    try:
        c.execute("SELECT affinity, since, tier FROM relations WHERE target_id=%s", (tid,))
        rel = c.fetchone()
    except Exception:
        rel = None

    if not rel:
        return legacy

    fresh = {}
    if rel.get("affinity") is not None:
        fresh["affinity"] = float(rel["affinity"])
    if rel.get("since") is not None:
        fresh["since"] = str(rel["since"])
    if rel.get("tier"):
        fresh["tier"] = rel["tier"]

    if not legacy:
        import json
        return json.dumps(fresh, ensure_ascii=False)
    try:
        import json
        data = json.loads(legacy)
        if not isinstance(data, dict):
            data = {}
        data.update(fresh)
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return legacy


def save_relation(tid, payload):
    """覆盖写亲密度（一人一行）"""
    c = get_cursor()
    c.execute("DELETE FROM events WHERE target_id=%s AND kind='rel'", (str(tid),))
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,'','rel',%s,NOW())",
        (str(tid), payload, dedupe_key(str(tid), "rel", "relation")),
    )
    c.connection.commit()
    dual_write("rel", tid, payload)

def load_today_life():
    """取今天的生活事件（v10-U9b 分享生活用）"""
    c = get_cursor()
    c.execute(
        "SELECT event_summary FROM events "
        "WHERE target_id=%s AND kind='life' AND tags='生活' AND DATE(created_at)=CURDATE() "
        "ORDER BY id DESC LIMIT 5",
        (STATE_TARGET,),
    )
    return [r["event_summary"] for r in c.fetchall()]


def load_agenda_items():
    """取出她的待办（v10-U9b）"""
    c = get_cursor()
    c.execute(
        "SELECT id, event_summary FROM events WHERE target_id=%s AND kind='agenda' ORDER BY id",
        (STATE_TARGET,),
    )
    return list(c.fetchall())


def delete_agenda_item(item_id):
    """删掉一条待办"""
    c = get_cursor()
    c.execute("DELETE FROM events WHERE id=%s AND kind='agenda'", (item_id,))
    c.connection.commit()


def load_timeline(tid, days=7, limit=12):
    """最近 N 天的记忆，按时间倒序（v8-B16）"""
    c = get_cursor()
    c.execute("""
        SELECT DATE(COALESCE(last_seen, created_at)) AS day,
               event_summary AS summary
        FROM events
        WHERE target_id IN (%s, %s) AND kind IN ('event', 'life', 'photo')
          AND COALESCE(last_seen, created_at) >= NOW() - INTERVAL %s DAY
        ORDER BY COALESCE(last_seen, created_at) DESC
        LIMIT %s
    """, (tid, STATE_TARGET, days, limit))
    return list(c.fetchall())


def load_memories_for_search(tid, limit=300):
    """取一批候选记忆喂给检索器（v8-B11）"""
    c = get_cursor()
    c.execute("""
        SELECT id, kind, event_summary AS summary, tags, importance, hit_count,
               created_at, last_seen
        FROM events
        WHERE target_id IN (%s, %s) AND kind IN ('event','life','promise','photo')
        ORDER BY id DESC LIMIT %s
    """, (tid, STATE_TARGET, limit))
    return list(c.fetchall())


def add_event_to_db(tid, event_summary, tags="", kind="event", importance=3, due_date=None):
    """写入一条记忆（v7-B15）

    - 7 天窗口内命中同一 dedupe_key → 只累加 hit_count、更新 last_seen
    - 否则插入新行，并按 kind 的上限裁剪最旧的
    """
    if not event_summary:
        return None
    c = get_cursor()
    key = dedupe_key(tid, kind, event_summary)
    now = datetime.now(CST)

    c.execute("""
        SELECT id FROM events
        WHERE target_id=%s AND kind=%s AND dedupe_key=%s
          AND COALESCE(last_seen, created_at) >= %s
        ORDER BY id LIMIT 1
    """, (tid, kind, key, now - timedelta(days=DEDUPE_WINDOW_DAYS)))
    hit = c.fetchone()
    if hit:  # 命中：不新增，只记账
        c.execute("UPDATE events SET hit_count=hit_count+1, last_seen=%s WHERE id=%s", (now, hit["id"]))
        c.connection.commit()
        return hit["id"]

    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, importance, due_date, last_seen) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (tid, event_summary, tags, kind, key, importance, due_date, now),
    )
    # 按 kind 分别保留
    keep = KIND_LIMITS.get(kind, KIND_LIMIT_DEFAULT)
    c.execute(
        "DELETE FROM events WHERE id NOT IN("
        "SELECT id FROM(SELECT id FROM events WHERE target_id=%s AND kind=%s ORDER BY id DESC LIMIT %s)AS tmp"
        ")AND target_id=%s AND kind=%s",
        (tid, kind, keep, tid, kind),
    )
    c.connection.commit()
    return None

# ===================== 双写（v17.4） =====================
# 写旧表之后，顺手写一份到新表。失败只记日志，绝不影响旧路径。
# 等 v17.5 验证够了，再把旧写入删掉。

_JSON_TABLES = {
    "state": ("bot_states", ("mood", "energy", "lonely")),
    "rel": ("relations", ("affinity", "since", "tier")),
    "friction": ("friction_states", ("expect_ts", "expect_text", "disappoint",
                                     "cold_ts", "last_grudge")),
    "reading": ("reading_progress", ("title", "intro", "last_no", "last_chapter")),
}


def dual_write(kind, tid, payload):
    """把 JSON payload 拆到新表；失败静默"""
    conf = _JSON_TABLES.get(kind)
    if not conf:
        return False
    table, fields = conf
    try:
        import json

        data = json.loads(payload) if payload else {}
        if not isinstance(data, dict):
            return False
        row = {"target_id": str(tid)}
        row.update({k: v for k, v in data.items() if k in fields})
        if len(row) <= 1:
            return False
        cols = list(row)
        ph = ",".join(["%s"] * len(cols))
        updates = ",".join(f"{k}=VALUES({k})" for k in cols if k != "target_id")
        sql = f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})"
        if updates:
            sql += f" ON DUPLICATE KEY UPDATE {updates}"
        c = get_cursor()
        c.execute(sql, tuple(row[k] for k in cols))
        c.connection.commit()
        return True
    except Exception as e:
        log_api(f"[双写] {kind} → {table} 失败（忽略）：{e}")
        return False
