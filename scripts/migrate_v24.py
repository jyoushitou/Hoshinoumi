# ===================== v23.5.0 owner user_id → MASTER_QQ =====================
# 执行前必须备份数据库；迁移用户/身份/邀请/审计/所有业务表。

from bot.infra import tenant
from scripts.migrate_v23 import USER_TABLES

OLD = "__owner__"


def apply(c):
    new = tenant.owner_id()
    if new == OLD:
        return {"old": OLD, "new": new, "changed": 0}
    changed = 0
    tables = [t for t, _ in USER_TABLES] + ["relation_events"]
    for table in tables:
        try:
            c.execute(f"UPDATE {table} SET user_id=%s WHERE user_id=%s", (new, OLD))
            changed += int(getattr(c, "rowcount", 0) or 0)
        except Exception:
            pass
    for sql in (
        "UPDATE identities SET user_id=%s WHERE user_id=%s",
        "UPDATE invites SET created_by=%s WHERE created_by=%s",
        "UPDATE invites SET used_by=%s WHERE used_by=%s",
        "UPDATE gateway_log SET owner=%s WHERE owner=%s",
    ):
        try:
            c.execute(sql, (new, OLD))
            changed += int(getattr(c, "rowcount", 0) or 0)
        except Exception:
            pass
    try:
        c.execute("SELECT id FROM users WHERE id=%s", (new,))
        if not c.fetchone():
            c.execute("UPDATE users SET id=%s WHERE id=%s", (new, OLD))
    except Exception:
        pass
    c.connection.commit()
    return {"old": OLD, "new": new, "changed": changed}
