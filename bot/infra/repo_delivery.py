# ===================== DeliveryHub 仓储（v35.2.1） =====================
# 只做 SQL；路由/编排在 delivery.hub 与 server.routes_endpoints。

from .conn import get_cursor


def _commit(c):
    try:
        c.connection.commit()
    except Exception:
        pass


def create_endpoint(user_id, name, kind, token_hash):
    c = get_cursor()
    try:
        c.execute(
            "INSERT INTO client_endpoints(user_id,name,kind,token_hash,enabled) "
            "VALUES(%s,%s,%s,%s,1)",
            (user_id, name, kind, token_hash),
        )
        _commit(c)
        return {"id": getattr(c, "lastrowid", None), "name": name, "kind": kind}
    finally:
        c.close()


def list_endpoints(user_id):
    c = get_cursor()
    try:
        c.execute(
            "SELECT id,name,kind,enabled,last_seen,created_at "
            "FROM client_endpoints WHERE user_id=%s ORDER BY id",
            (user_id,),
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        c.close()


def endpoint_by_id(user_id, endpoint_id):
    c = get_cursor()
    try:
        c.execute(
            "SELECT id,user_id,name,kind,token_hash,enabled,last_seen "
            "FROM client_endpoints WHERE user_id=%s AND id=%s",
            (user_id, endpoint_id),
        )
        return c.fetchone()
    finally:
        c.close()


def disable_endpoint(user_id, endpoint_id):
    c = get_cursor()
    try:
        c.execute(
            "UPDATE client_endpoints SET enabled=0 WHERE user_id=%s AND id=%s",
            (user_id, endpoint_id),
        )
        _commit(c)
        return int(getattr(c, "rowcount", 0) or 0) > 0
    finally:
        c.close()


def enabled_endpoints(user_id):
    c = get_cursor()
    try:
        c.execute(
            "SELECT id,name,kind FROM client_endpoints "
            "WHERE user_id=%s AND enabled=1 ORDER BY id",
            (user_id,),
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        c.close()


def enqueue(user_id, endpoint_id, message_id, target_id, channel, payload_json):
    """幂等入队；返回 1 表示新插入，0 表示已存在。"""
    c = get_cursor()
    try:
        from .conn import _SQLiteCursor
        sql = ("INSERT OR IGNORE INTO delivery_outbox"
               "(user_id,endpoint_id,message_id,target_id,channel,payload_json,status) "
               "VALUES(%s,%s,%s,%s,%s,%s,'pending')")
        if not isinstance(c, _SQLiteCursor):
            sql = sql.replace("INSERT OR IGNORE", "INSERT IGNORE")
        c.execute(sql, (user_id, endpoint_id, message_id, str(target_id),
                        channel, payload_json))
        _commit(c)
        return 1 if int(getattr(c, "rowcount", 0) or 0) > 0 else 0
    finally:
        c.close()


def pull(user_id, endpoint_id, after_id=0, limit=50):
    limit = max(1, min(int(limit or 50), 200))
    c = get_cursor()
    try:
        c.execute(
            "SELECT id,endpoint_id,message_id,target_id,channel,payload_json,status,created_at "
            "FROM delivery_outbox WHERE user_id=%s AND endpoint_id=%s AND id>%s "
            "AND status IN ('pending','sent') ORDER BY id LIMIT %s",
            (user_id, endpoint_id, int(after_id or 0), limit),
        )
        rows = [dict(r) for r in c.fetchall()]
        if rows:
            c.execute(
                "UPDATE delivery_outbox SET status='sent', attempts=attempts+1 "
                "WHERE user_id=%s AND endpoint_id=%s AND status='pending' AND id<=%s",
                (user_id, endpoint_id, int(rows[-1]["id"])),
            )
            c.execute(
                "UPDATE client_endpoints SET last_seen=CURRENT_TIMESTAMP "
                "WHERE user_id=%s AND id=%s",
                (user_id, endpoint_id),
            )
            _commit(c)
        return rows
    finally:
        c.close()


def ack(user_id, endpoint_id, message_id):
    c = get_cursor()
    try:
        c.execute(
            "UPDATE delivery_outbox SET status='delivered', delivered_at=CURRENT_TIMESTAMP "
            "WHERE user_id=%s AND endpoint_id=%s AND message_id=%s",
            (user_id, endpoint_id, str(message_id)),
        )
        _commit(c)
        return int(getattr(c, "rowcount", 0) or 0) > 0
    finally:
        c.close()
