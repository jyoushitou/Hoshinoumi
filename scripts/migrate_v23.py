# ===================== v23.1 业务表 user_id =====================
# 只做列、索引、回填；仓储强制过滤在 v23.2。
# 老库所有存量行回填 __owner__，不丢数据。

USER_TABLES = [
    ("memories", "target_id"),
    ("facts", "target_id"),
    ("diaries", "target_id"),
    ("reading_progress", "target_id"),
    ("relations", "target_id"),
    ("friction_states", "target_id"),
    ("bot_states", "target_id"),
    ("habits", "target_id"),
    ("cron_tasks", "target_id"),
    ("cron_overrides", "target_id"),
    ("targets", "target_id"),
    ("user_memory", "target_id"),
    ("keywords", "target_id"),
    ("digests", "target_id"),
    ("conversation_messages", "target_id"),
]

OWNER = "__owner__"


def _columns(c, table):
    """返回列名集合；两种后端都走一次 SELECT LIMIT 1 太脏，直接用方言查询"""
    from bot.infra.conn import _resolve_backend
    backend = _resolve_backend()
    if backend == "sqlite":
        c.execute(f"PRAGMA table_info({table})")
        return {r["name"] for r in (c.fetchall() or [])}
    c.execute(
        "SELECT COLUMN_NAME AS name FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", (table,))
    return {r["name"] for r in (c.fetchall() or [])}


def _table_exists(c, table):
    from bot.infra.conn import _resolve_backend
    if _resolve_backend() == "sqlite":
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table,))
        return c.fetchone() is not None
    c.execute(
        "SELECT TABLE_NAME AS name FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", (table,))
    return c.fetchone() is not None


def _add_column(c, table):
    if not _table_exists(c, table):
        return False
    cols = _columns(c, table)
    if "user_id" in cols:
        return False
    c.execute(
        f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(64) "
        "NOT NULL DEFAULT '__owner__'")
    return True


def _add_index(c, table, target_col):
    try:
        if target_col:
            c.execute(
                f"CREATE INDEX idx_{table}_user_target ON {table}(user_id, {target_col})")
        else:
            c.execute(f"CREATE INDEX idx_{table}_user ON {table}(user_id)")
    except Exception:
        # 索引已存在 / SQLite 旧版本没有 IF NOT EXISTS
        pass


def _add_speaker(c):
    table = "conversation_messages"
    if not _table_exists(c, table):
        return False
    if "speaker_id" in _columns(c, table):
        return False
    c.execute(f"ALTER TABLE {table} ADD COLUMN speaker_id VARCHAR(64) NULL")
    return True


def _add_password(c):
    table = "users"
    if not _table_exists(c, table):
        return False
    if "password_hash" in _columns(c, table):
        return False
    c.execute(f"ALTER TABLE {table} ADD COLUMN password_hash VARCHAR(255) NULL")
    return True


def apply(c):
    made = []
    for table, target_col in USER_TABLES:
        if not _table_exists(c, table):
            continue
        if _add_column(c, table):
            made.append(table)
        _add_index(c, table, target_col)
        # 老库显式补默认；新列已有 DEFAULT，但清一次空值更稳
        c.execute(
            f"UPDATE {table} SET user_id=%s "
            "WHERE user_id IS NULL OR user_id=''", (OWNER,))
    if _add_speaker(c) and "conversation_messages" not in made:
        made.append("conversation_messages.speaker_id")
    if _add_password(c) and "users.password_hash" not in made:
        made.append("users.password_hash")
    c.connection.commit()
    return made
