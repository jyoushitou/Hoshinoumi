# ===================== 账号 / 身份 / 角色（v23.0） =====================
# 单用户时代的主人是 __owner__；v23 引入 users/identities/roles。
# 所有函数不依赖 MySQL 方言：用 SELECT + INSERT/UPDATE，SQLite/MySQL 都能跑。

from ..log import log_api

OWNER_ID = "__owner__"
ROLES = {
    "owner": ("主人", "all"),
    "admin": ("管理员", "manage_users,read_all"),
    "user": ("普通用户", "chat,memory,ledger"),
}


def _close(c):
    try:
        c.close()
    except Exception:
        pass


def _get_cursor(cursor):
    if cursor is not None:
        return cursor, False
    from .conn import get_cursor
    return get_cursor(), True


def _one(c, sql, params):
    c.execute(sql, params)
    return c.fetchone()


def _insert_ignore(c, sql, params):
    """跨方言的 INSERT IGNORE / INSERT OR IGNORE"""
    try:
        from .conn import _resolve_backend
        sqlite = _resolve_backend() == "sqlite"
    except Exception:
        sqlite = False
    if sqlite:
        c.execute(sql.replace("INSERT IGNORE", "INSERT OR IGNORE"), params)
    else:
        c.execute(sql, params)


def ensure_defaults(cursor=None):
    """幂等：roles + owner 用户 + owner 的 QQ 身份"""
    from ..config import MASTER_QQ

    c, owned = _get_cursor(cursor)
    try:
        for name, (display, perms) in ROLES.items():
            _insert_ignore(
                c,
                "INSERT IGNORE INTO roles(name, display_name, permissions) VALUES(%s,%s,%s)",
                (name, display, perms))
        _insert_ignore(
            c,
            "INSERT IGNORE INTO users(id, nickname, role, status) VALUES(%s,%s,%s,%s)",
            (OWNER_ID, "owner", "owner", "active"))
        if int(MASTER_QQ or 0) > 0:
            _insert_ignore(
                c,
                "INSERT IGNORE INTO identities(user_id, channel, external_id) VALUES(%s,%s,%s)",
                (OWNER_ID, "qq", str(MASTER_QQ)))
        c.connection.commit()
        return True
    except Exception as e:
        try:
            c.connection.rollback()
        except Exception:
            pass
        log_api(f"[账号] 初始化失败: {e}")
        return False
    finally:
        if owned:
            _close(c)


def get(user_id, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        return _one(c, "SELECT id,nickname,password_hash,role,status,created_at FROM users WHERE id=%s",
                    (str(user_id),))
    finally:
        if owned:
            _close(c)


def create(user_id, nickname="", role="user", status="active", cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        _insert_ignore(
            c,
            "INSERT IGNORE INTO users(id, nickname, role, status) VALUES(%s,%s,%s,%s)",
            (str(user_id), str(nickname or user_id), str(role), str(status)))
        c.connection.commit()
        return get(user_id, c)
    finally:
        if owned:
            _close(c)


def set_status(user_id, status, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute("UPDATE users SET status=%s WHERE id=%s", (str(status), str(user_id)))
        c.connection.commit()
        return c.rowcount > 0
    finally:
        if owned:
            _close(c)


def set_role(user_id, role, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute("UPDATE users SET role=%s WHERE id=%s", (str(role), str(user_id)))
        c.connection.commit()
        return c.rowcount > 0
    finally:
        if owned:
            _close(c)


def list_users(cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute("SELECT id,nickname,role,status,created_at FROM users ORDER BY created_at")
        return list(c.fetchall() or [])
    finally:
        if owned:
            _close(c)


def bind_identity(user_id, channel, external_id, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        _insert_ignore(
            c,
            "INSERT IGNORE INTO identities(user_id, channel, external_id) VALUES(%s,%s,%s)",
            (str(user_id), str(channel), str(external_id)))
        c.connection.commit()
        return resolve_identity(channel, external_id, c) is not None
    finally:
        if owned:
            _close(c)


def resolve_identity(channel, external_id, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute(
            "SELECT user_id FROM identities WHERE channel=%s AND external_id=%s",
            (str(channel), str(external_id)))
        row = c.fetchone()
        return row["user_id"] if row else None
    finally:
        if owned:
            _close(c)


def identities_of(user_id, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute("SELECT channel,external_id,created_at FROM identities WHERE user_id=%s",
                  (str(user_id),))
        return list(c.fetchall() or [])
    finally:
        if owned:
            _close(c)


def create_invite(code, role="user", created_by=OWNER_ID, expires_at=None, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        _insert_ignore(
            c,
            "INSERT IGNORE INTO invites(code, role, created_by, expires_at) VALUES(%s,%s,%s,%s)",
            (str(code), str(role), str(created_by), expires_at))
        c.connection.commit()
        return True
    finally:
        if owned:
            _close(c)


def consume_invite(code, user_id, cursor=None):
    """核销邀请码；成功返回 role，失败返回 None"""
    c, owned = _get_cursor(cursor)
    try:
        c.execute(
            "SELECT role,used_by,expires_at FROM invites WHERE code=%s", (str(code),))
        row = c.fetchone()
        if not row or row.get("used_by"):
            return None
        if row.get("expires_at"):
            c.execute("SELECT CURRENT_TIMESTAMP AS now")
            # 交给上层/数据库比较太依赖时区；这里只做「已过期」由调用方预判
        role = row["role"]
        c.execute("UPDATE invites SET used_by=%s WHERE code=%s AND used_by IS NULL",
                  (str(user_id), str(code)))
        c.connection.commit()
        return role if c.rowcount > 0 else None
    finally:
        if owned:
            _close(c)

# ===================== 密码（v23.3） =====================
def hash_password(password):
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    iterations = 120000
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"),
                                 salt.encode("ascii"), iterations).hex()
    return f"pbkdf2${iterations}${salt}${digest}"


def verify_password(password, stored):
    import hashlib
    import hmac
    try:
        algo, iterations, salt, expected = str(stored or "").split("$", 3)
        if algo != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"),
                                     salt.encode("ascii"), int(iterations)).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def set_password(user_id, password, cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        c.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                  (hash_password(password), str(user_id)))
        c.connection.commit()
        return c.rowcount > 0
    finally:
        if owned:
            _close(c)


def create_with_password(user_id, password, nickname="", role="user", cursor=None):
    c, owned = _get_cursor(cursor)
    try:
        _insert_ignore(
            c,
            "INSERT IGNORE INTO users(id, nickname, password_hash, role, status) "
            "VALUES(%s,%s,%s,%s,%s)",
            (str(user_id), str(nickname or user_id), hash_password(password),
             str(role), "active"))
        c.connection.commit()
        return get(user_id, c)
    finally:
        if owned:
            _close(c)



