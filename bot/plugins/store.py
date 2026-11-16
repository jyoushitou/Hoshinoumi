# ===================== 插件注册表存储（v28.4） =====================

from dataclasses import dataclass

from .errors import PluginLoadError


@dataclass(frozen=True)
class DbPlugin:
    name: str
    author: str
    layer: str
    version: str
    capabilities: tuple
    entrypoint: str
    path: str
    package_hash: str
    enabled: bool
    auto_start: bool


class PluginStore:
    def __init__(self, cursor_factory=None):
        self._cursor_factory = cursor_factory

    def _cursor(self):
        if self._cursor_factory:
            return self._cursor_factory()
        from ..infra.conn import get_cursor
        return get_cursor()

    def get(self, name):
        c = self._cursor()
        try:
            c.execute(
                "SELECT name,author,layer,version,capabilities,entrypoint,"
                "path,package_hash,enabled,auto_start FROM plugin_registry "
                "WHERE name=%s", (str(name),))
            row = c.fetchone()
            if not row:
                return None
            return DbPlugin(
                name=row["name"], author=row["author"], layer=row["layer"],
                version=row["version"],
                capabilities=tuple((row.get("capabilities") or "").split(","))
                if row.get("capabilities") else (),
                entrypoint=row["entrypoint"], path=row.get("path") or "",
                package_hash=row.get("package_hash") or "",
                enabled=bool(row.get("enabled")), auto_start=bool(row.get("auto_start")),
            )
        finally:
            try:
                c.close()
            except Exception:
                pass

    def list(self, enabled_only=False):
        c = self._cursor()
        try:
            sql = ("SELECT name,author,layer,version,capabilities,entrypoint,"
                   "path,package_hash,enabled,auto_start FROM plugin_registry")
            if enabled_only:
                sql += " WHERE enabled=1"
            sql += " ORDER BY name"
            c.execute(sql)
            rows = c.fetchall() or []
        finally:
            try:
                c.close()
            except Exception:
                pass
        out = []
        for row in rows:
            out.append(DbPlugin(
                name=row["name"], author=row["author"], layer=row["layer"],
                version=row["version"],
                capabilities=tuple((row.get("capabilities") or "").split(","))
                if row.get("capabilities") else (),
                entrypoint=row["entrypoint"], path=row.get("path") or "",
                package_hash=row.get("package_hash") or "",
                enabled=bool(row.get("enabled")), auto_start=bool(row.get("auto_start")),
            ))
        return out

    def insert(self, manifest, package_hash, path="", enabled=False):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO plugin_registry"
                "(name,author,layer,version,api_version,requires_core,capabilities,"
                "entrypoint,path,package_hash,auto_start,enabled) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (manifest.name, manifest.author, manifest.layer, manifest.version,
                 int(manifest.api_version), manifest.requires_core,
                 ",".join(manifest.capabilities), manifest.entrypoint,
                 path, package_hash, int(bool(manifest.auto_start)), int(bool(enabled))))
            c.connection.commit()
        except Exception as e:
            raise PluginLoadError(f"写入 plugin_registry 失败：{e}") from e
        finally:
            try:
                c.close()
            except Exception:
                pass
        self.bump_generation()

    def set_enabled(self, name, enabled):
        c = self._cursor()
        try:
            c.execute("UPDATE plugin_registry SET enabled=%s WHERE name=%s",
                      (int(bool(enabled)), str(name)))
            c.connection.commit()
        finally:
            try:
                c.close()
            except Exception:
                pass
        self.bump_generation()

    def generation(self):
        c = self._cursor()
        try:
            c.execute("SELECT generation FROM plugin_registry_generation WHERE id=1")
            row = c.fetchone()
            return int(row["generation"]) if row else 0
        finally:
            try:
                c.close()
            except Exception:
                pass

    def bump_generation(self):
        c = self._cursor()
        try:
            c.execute("UPDATE plugin_registry_generation SET generation=generation+1 WHERE id=1")
            if getattr(c, "rowcount", 0) == 0:
                c.execute("INSERT INTO plugin_registry_generation(id,generation) VALUES(1,1)")
            c.connection.commit()
        finally:
            try:
                c.close()
            except Exception:
                pass
        return self.generation()

    def add_approval(self, name, action="install", requested_by="__owner__"):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO plugin_approvals(plugin_name,action,status,requested_by) "
                "VALUES(%s,%s,'pending',%s)", (str(name), str(action), str(requested_by)))
            c.connection.commit()
            return getattr(c, "lastrowid", None)
        finally:
            try:
                c.close()
            except Exception:
                pass

    def pending_approvals(self):
        c = self._cursor()
        try:
            c.execute("SELECT id,plugin_name,action,status,created_at "
                      "FROM plugin_approvals WHERE status='pending' ORDER BY id")
            return c.fetchall() or []
        finally:
            try:
                c.close()
            except Exception:
                pass

    def decide(self, approval_id, status, decided_by="__owner__"):
        if status not in ("approved", "rejected"):
            raise ValueError("status 必须是 approved/rejected")
        c = self._cursor()
        try:
            c.execute(
                "UPDATE plugin_approvals SET status=%s, decided_by=%s, "
                "decided_at=CURRENT_TIMESTAMP WHERE id=%s",
                (status, str(decided_by), int(approval_id)))
            c.connection.commit()
            return getattr(c, "rowcount", 0) > 0
        finally:
            try:
                c.close()
            except Exception:
                pass

    def set_auto_start(self, name, enabled):
        c = self._cursor()
        try:
            c.execute("UPDATE plugin_registry SET auto_start=%s WHERE name=%s",
                      (int(bool(enabled)), str(name)))
            c.connection.commit()
        finally:
            try:
                c.close()
            except Exception:
                pass

    def errors(self, name=None, limit=50):
        c = self._cursor()
        try:
            if name:
                c.execute("SELECT plugin_name,error_type,message,created_at "
                          "FROM plugin_errors WHERE plugin_name=%s ORDER BY id DESC LIMIT %s",
                          (str(name), int(limit)))
            else:
                c.execute("SELECT plugin_name,error_type,message,created_at "
                          "FROM plugin_errors ORDER BY id DESC LIMIT %s", (int(limit),))
            return c.fetchall() or []
        finally:
            try:
                c.close()
            except Exception:
                pass

    def record_error(self, name, error_type, message, traceback="", fail_limit=5):
        c = self._cursor()
        try:
            c.execute(
                "INSERT INTO plugin_errors(plugin_name,error_type,message,traceback) "
                "VALUES(%s,%s,%s,%s)", (str(name), str(error_type), str(message), str(traceback)))
            c.connection.commit()
        except Exception:
            pass
        finally:
            try:
                c.close()
            except Exception:
                pass
        # 连续失败达到阈值自动停用；不自动恢复
        try:
            n = len(self.errors(name, limit=int(fail_limit)))
            if n >= int(fail_limit):
                self.set_enabled(name, False)
        except Exception:
            pass

    def auto_start_names(self):
        return [p.name for p in self.list(enabled_only=True) if p.auto_start]
