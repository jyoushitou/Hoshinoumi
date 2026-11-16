# ===================== 存储路由（v33.3.2） =====================

from ..plugins.permissions import PermissionDenied, PermissionRequired
from ..registry import PluginRegistry
from .native import MetaRepository, SQLStorage


class StorageRouter:
    def __init__(self, registry=None, plugin_factory=None, plugin_store=None):
        self.registry = registry or PluginRegistry()
        self._factory = plugin_factory
        self.plugin_store = plugin_store
        self._cache = {}
        self._native = {"storage.backend": SQLStorage(), "storage.repository": MetaRepository()}

    def native(self, kind):
        return self._native.get(kind)

    def get(self, kind, name):
        cap = f"{kind}.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(kind)
        if self.plugin_store is not None:
            try:
                db = self.plugin_store.get(rec.name)
                if db is not None and not db.enabled:
                    return self.native(kind)
            except Exception:
                pass
        key = (kind, rec.name)
        if key in self._cache:
            return self._cache[key]
        try:
            if self._factory is not None:
                obj = self._factory(rec)
            else:
                from ..plugins.context import make_context
                ctx = make_context(rec.manifest, registry=self.registry)
                ctx.permissions.require("plugin.call", cap)
                obj = rec.factory(ctx)
        except (PermissionDenied, PermissionRequired):
            return self.native(kind)
        except Exception:
            return self.native(kind)
        if obj is None:
            return self.native(kind)
        self._cache[key] = obj
        return obj

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if k[1] != name}
