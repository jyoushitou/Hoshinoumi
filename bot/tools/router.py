# ===================== 工具路由（v33.2.2） =====================

from ..plugins.permissions import PermissionDenied, PermissionRequired
from ..registry import PluginRegistry
from .native import EchoTool


class ToolRouter:
    def __init__(self, registry=None, plugin_factory=None, plugin_store=None):
        self.registry = registry or PluginRegistry()
        self._factory = plugin_factory
        self.plugin_store = plugin_store
        self._cache = {}
        self._native = {"echo": EchoTool()}

    def native(self, name="echo"):
        return self._native.get(str(name))

    def get(self, name="echo"):
        cap = f"tool.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(name)
        if self.plugin_store is not None:
            try:
                db = self.plugin_store.get(rec.name)
                if db is not None and not db.enabled:
                    return self.native(name)
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
            return self.native(name)
        except Exception:
            return self.native(name)
        if obj is None:
            return self.native(name)
        self._cache[rec.name] = obj
        return obj

    async def invoke(self, name, user_id, args):
        tool = self.get(name)
        if tool is None:
            return {"ok": False, "error": "no such tool"}
        try:
            return await tool.invoke(user_id, args)
        except Exception as e:
            rec = self.registry.get(f"tool.{name}@1")
            if rec is not None and self.plugin_store is not None:
                try:
                    self.plugin_store.record_error(rec.name, type(e).__name__, str(e))
                except Exception:
                    pass
            self._cache.pop(name, None)
            native = self.native(name)
            if native is not None and native is not tool:
                return await native.invoke(user_id, args)
            return {"ok": False, "error": str(e)}

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(str(name), None)
