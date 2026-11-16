# ===================== 插件权限（v28.3） =====================
# 0 拒绝 / 1 需要审批 / 2 允许。没有记录时默认 1。

import fnmatch

from .errors import PermissionDenied, PermissionRequired

KNOWN = {
    "config.read", "config.secret",
    "db.read", "db.write",
    "file.read", "file.write",
    "network.outbound",
    "event.read", "event.emit",
    "plugin.call",
}


def _match(stored, requested):
    if stored == "*" or stored == requested:
        return True
    if fnmatch.fnmatchcase(requested, stored):
        return True
    # network scope：example.com 允许其子域；*.example.com 走 fnmatch
    if stored.startswith("."):
        return requested == stored[1:] or requested.endswith(stored)
    return False


class PermissionStore:
    def __init__(self, plugin_name):
        self.plugin_name = str(plugin_name)

    def list(self):
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute(
                "SELECT permission, scope, level FROM plugin_permissions "
                "WHERE plugin_name=%s ORDER BY permission, scope",
                (self.plugin_name,))
            return [dict(r) for r in (c.fetchall() or [])]
        finally:
            try:
                c.close()
            except Exception:
                pass

    def set(self, permission, scope="", level=1):
        if permission not in KNOWN:
            raise ValueError(f"未知权限：{permission}")
        if int(level) not in (0, 1, 2):
            raise ValueError("level 只能是 0/1/2")
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute(
                "DELETE FROM plugin_permissions "
                "WHERE plugin_name=%s AND permission=%s AND scope=%s",
                (self.plugin_name, permission, str(scope or "")))
            c.execute(
                "INSERT INTO plugin_permissions(plugin_name, permission, scope, level) "
                "VALUES(%s,%s,%s,%s)",
                (self.plugin_name, permission, str(scope or ""), int(level)))
            c.connection.commit()
        finally:
            try:
                c.close()
            except Exception:
                pass

    def level(self, permission, scope=""):
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute(
                "SELECT scope, level FROM plugin_permissions "
                "WHERE plugin_name=%s AND permission=%s",
                (self.plugin_name, permission))
            rows = c.fetchall() or []
        finally:
            try:
                c.close()
            except Exception:
                pass
        exact = None
        wildcard = None
        for row in rows:
            stored = str(row.get("scope") or "")
            if stored == str(scope or ""):
                exact = int(row.get("level") or 0)
            elif _match(stored, str(scope or "")):
                wildcard = max(wildcard or 0, int(row.get("level") or 0))
        if exact is not None:
            return exact
        if wildcard is not None:
            return wildcard
        return 1

    def require(self, permission, scope=""):
        if permission not in KNOWN:
            raise PermissionDenied(f"未知权限：{permission}")
        level = self.level(permission, scope)
        if level == 0:
            raise PermissionDenied(f"{self.plugin_name} 被拒绝：{permission} {scope}")
        if level == 1:
            raise PermissionRequired(
                f"{self.plugin_name} 需要审批：{permission} {scope}")
        return True
