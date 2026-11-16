# ===================== 调度路由（v33.4.2） =====================

from ..plugins.permissions import PermissionDenied, PermissionRequired
from ..registry import PluginRegistry
from .native import AsyncioScheduler


class SchedulerRouter:
    def __init__(self, registry=None, plugin_factory=None, plugin_store=None):
        self.registry = registry or PluginRegistry()
        self._factory = plugin_factory
        self.plugin_store = plugin_store
        self._cache = {}
        self._native = AsyncioScheduler()

    def native(self):
        return self._native

    def get(self, name="asyncio"):
        cap = f"scheduler.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self._native
        if self.plugin_store is not None:
            try:
                db = self.plugin_store.get(rec.name)
                if db is not None and not db.enabled:
                    return self._native
            except Exception:
                pass
        if rec.name in self._cache:
            return self._cache[rec.name]
        try:
            if self._factory is not None:
                obj = self._factory(rec)
            else:
                from ..plugins.context import make_context
                ctx = make_context(rec.manifest, registry=self.registry)
                ctx.permissions.require("plugin.call", cap)
                obj = rec.factory(ctx)
        except (PermissionDenied, PermissionRequired):
            return self._native
        except Exception:
            return self._native
        if obj is None:
            return self._native
        self._cache[rec.name] = obj
        return obj

    def invalidate(self, name=None):
        self._cache.clear() if name is None else self._cache.pop(str(name), None)
