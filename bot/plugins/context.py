# ===================== PluginContext（v28.3） =====================
# 所有能力都从 context 入口走；越权在入口直接拒绝。

import fnmatch
import os
from pathlib import Path
from urllib.parse import urlparse

from .errors import PermissionDenied, PermissionRequired
from .permissions import PermissionStore
from .tasks import PluginTasks

ROOT = Path(__file__).resolve().parent.parent.parent


def _check_table(plugin_name, table):
    table = str(table or "")
    if not table.startswith(f"plugin_{plugin_name}_"):
        raise PermissionDenied(f"插件只能访问 plugin_{plugin_name}_* 表：{table}")
    return table


class ConfigPort:
    def __init__(self, perms):
        self._perms = perms

    def get(self, key, default=None):
        if "secret" in str(key).lower() or "key" in str(key).lower():
            self._perms.require("config.secret", str(key))
        from ..core import settings
        return settings.get(str(key), default)

    def require(self, key):
        value = self.get(key, None)
        if value is None:
            raise KeyError(key)
        return value


class DbPort:
    def __init__(self, plugin_name, perms):
        self.plugin_name = plugin_name
        self._perms = perms

    def select(self, table, columns="*", where="", params=(), limit=100):
        table = _check_table(self.plugin_name, table)
        self._perms.require("db.read", table)
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            sql = f"SELECT {columns} FROM {table}"
            if where:
                sql += f" WHERE {where}"
            sql += " LIMIT %s"
            c.execute(sql, tuple(params) + (int(limit),))
            return c.fetchall() or []
        finally:
            try:
                c.close()
            except Exception:
                pass

    def insert(self, table, values):
        table = _check_table(self.plugin_name, table)
        self._perms.require("db.write", table)
        cols = list(values)
        if not cols:
            raise ValueError("insert values 为空")
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            ph = ",".join(["%s"] * len(cols))
            c.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})",
                      tuple(values[k] for k in cols))
            c.connection.commit()
            return getattr(c, "lastrowid", None)
        finally:
            try:
                c.close()
            except Exception:
                pass

    def update(self, table, values, where, params=()):
        table = _check_table(self.plugin_name, table)
        self._perms.require("db.write", table)
        cols = list(values)
        if not cols or not where:
            raise ValueError("update 参数不完整")
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            sets = ",".join(f"{k}=%s" for k in cols)
            c.execute(f"UPDATE {table} SET {sets} WHERE {where}",
                      tuple(values[k] for k in cols) + tuple(params))
            c.connection.commit()
            return getattr(c, "rowcount", 0)
        finally:
            try:
                c.close()
            except Exception:
                pass

    def delete(self, table, where, params=()):
        table = _check_table(self.plugin_name, table)
        self._perms.require("db.write", table)
        if not where:
            raise ValueError("delete 必须带 where")
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute(f"DELETE FROM {table} WHERE {where}", tuple(params))
            c.connection.commit()
            return getattr(c, "rowcount", 0)
        finally:
            try:
                c.close()
            except Exception:
                pass


class FilePort:
    def __init__(self, manifest, perms):
        self.manifest = manifest
        self._perms = perms
        self.root = ROOT / "plugins" / manifest.layer / manifest.name / "data"

    def _path(self, rel):
        p = (self.root / str(rel)).resolve()
        if self.root.resolve() != p and self.root.resolve() not in p.parents:
            raise PermissionDenied(f"路径越界：{rel}")
        return p

    def _rel(self, path):
        return str(path.relative_to(self.root.resolve()))

    def read(self, path):
        p = self._path(path)
        rel = self._rel(p)
        self._perms.require("file.read", rel)
        return p.read_bytes()

    def write(self, path, data):
        p = self._path(path)
        rel = self._rel(p)
        self._perms.require("file.write", rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return str(p)

    def list(self, path="."):
        p = self._path(path)
        rel = self._rel(p) if p != self.root.resolve() else "*"
        self._perms.require("file.read", rel)
        return sorted(x.name for x in p.iterdir())


class NetworkPort:
    def __init__(self, perms):
        self._perms = perms

    async def request(self, method, url, **kwargs):
        host = (urlparse(str(url)).hostname or "").lower()
        self._perms.require("network.outbound", host)
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.request(method, url, **kwargs) as r:
                return {"status": r.status, "body": await r.read()}


class EventPort:
    def __init__(self, perms):
        self._perms = perms

    def emit(self, kind, payload):
        self._perms.require("event.emit", str(kind))
        from ..events import registry
        fn = getattr(registry, "emit", None)
        if fn:
            return fn(kind, payload)
        return None

    def on(self, kind, handler):
        self._perms.require("event.read", str(kind))
        from ..events import registry
        fn = getattr(registry, "on", None)
        if fn:
            return fn(kind, handler)
        raise RuntimeError("event registry 不支持 on")

    def off(self, kind, handler):
        from ..events import registry
        fn = getattr(registry, "off", None)
        if fn:
            return fn(kind, handler)
        return None


class LifecyclePort:
    def __init__(self):
        self._stops = []

    def on_stop(self, fn):
        self._stops.append(fn)
        return fn

    async def stop(self):
        for fn in reversed(self._stops):
            r = fn()
            if hasattr(r, "__await__"):
                await r


class LoggerPort:
    def __init__(self, name):
        self.name = name

    def _write(self, tag, msg):
        from ..log import log_api
        log_api(f"[插件:{self.name}] [{tag}] {msg}")

    def info(self, msg):
        self._write("INFO", msg)

    def error(self, msg):
        self._write("ERROR", msg)

    def warning(self, msg):
        self._write("WARN", msg)


class PluginContext:
    def __init__(self, manifest, registry=None, permissions=None):
        self.manifest = manifest
        self.permissions = permissions or PermissionStore(manifest.name)
        self.registry = registry
        self.config = ConfigPort(self.permissions)
        self.db = DbPort(manifest.name, self.permissions)
        self.files = FilePort(manifest, self.permissions)
        self.network = NetworkPort(self.permissions)
        self.events = EventPort(self.permissions)
        self.tasks = PluginTasks(f"plugin:{manifest.name}")
        self.lifecycle = LifecyclePort()
        self.logger = LoggerPort(manifest.name)
        # v28.5 之前，能力端口先给明确错误，避免插件误以为已实现
        self.ai = None
        self.memory = None
        self.storage = None

    def on_stop(self, fn):
        return self.lifecycle.on_stop(fn)


def make_context(manifest, registry=None, permissions=None):
    return PluginContext(manifest, registry=registry, permissions=permissions)
