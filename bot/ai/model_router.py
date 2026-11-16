# ===================== 模型层路由（v30） =====================
# 第三方 ModelProvider 走 PluginRegistry；核心 native 始终可回落。

from ..ports.models import ModelProvider, ModelRequest
from ..registry import PluginRegistry
from ..plugins.permissions import PermissionDenied, PermissionRequired
from .providers import DeepSeekProvider, DoubaoProvider

NATIVE = {
    "deepseek": DeepSeekProvider,
    "doubao": DoubaoProvider,
}


class ModelRouter:
    def __init__(self, registry=None, plugin_factory=None, store=None):
        self.registry = registry or PluginRegistry()
        self._plugin_factory = plugin_factory
        self.store = store
        self._cache = {}

    def native(self, name):
        cls = NATIVE.get(str(name))
        return cls() if cls else None

    def provider(self, name):
        cap = f"model.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(name)
        # v30.2：注册表里仍有对象，但 DB 已停用 → 不调用，回落 native
        if self.store is not None:
            try:
                db_rec = self.store.get(rec.name)
                if db_rec is not None and not db_rec.enabled:
                    return self.native(name)
            except Exception:
                pass
        if rec.name in self._cache:
            return self._cache[rec.name]
        try:
            if self._plugin_factory is not None:
                obj = self._plugin_factory(rec)
            else:
                from ..plugins.context import make_context
                ctx = make_context(rec.manifest, registry=self.registry)
                # v30.1：插件模型必须先获得 plugin.call 权限（默认 1=审批）
                ctx.permissions.require("plugin.call", cap)
                obj = rec.factory(ctx)
        except (PermissionDenied, PermissionRequired):
            return None
        except Exception as e:
            self._record_error(rec.name, e)
            return None
        if obj is not None:
            self._cache[rec.name] = obj
        return obj

    async def complete(self, name, req, fallback=True):
        p = self.provider(name)
        if p is not None:
            try:
                reply = await p.complete(req)
                if reply is not None:
                    return reply
            except Exception as e:
                rec = self.registry.get(f"model.{name}@1")
                if rec is not None:
                    self._record_error(rec.name, e)
                    self._cache.pop(rec.name, None)
                reply = None
        if fallback:
            native = self.native(name)
            if native is not None:
                return await native.complete(req)
        return None

    def _record_error(self, name, exc):
        if self.store is None:
            return
        try:
            self.store.record_error(name, type(exc).__name__, str(exc))
        except Exception:
            pass

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(str(name), None)
