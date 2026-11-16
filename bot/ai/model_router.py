# ===================== 模型层路由（v30） =====================
# 第三方 ModelProvider 走 PluginRegistry；核心 native 始终可回落。

from ..ports.models import ModelProvider, ModelRequest
from ..registry import PluginRegistry
from .providers import DeepSeekProvider, DoubaoProvider

NATIVE = {
    "deepseek": DeepSeekProvider,
    "doubao": DoubaoProvider,
}


class ModelRouter:
    def __init__(self, registry=None, plugin_factory=None):
        self.registry = registry or PluginRegistry()
        self._plugin_factory = plugin_factory
        self._cache = {}

    def native(self, name):
        cls = NATIVE.get(str(name))
        return cls() if cls else None

    def provider(self, name):
        cap = f"model.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(name)
        if rec.name in self._cache:
            return self._cache[rec.name]
        try:
            if self._plugin_factory is not None:
                obj = self._plugin_factory(rec)
            else:
                from ..plugins.context import make_context
                ctx = make_context(rec.manifest, registry=self.registry)
                obj = rec.factory(ctx)
        except Exception:
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
            except Exception:
                reply = None
        if fallback:
            native = self.native(name)
            if native is not None:
                return await native.complete(req)
        return None

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(str(name), None)
