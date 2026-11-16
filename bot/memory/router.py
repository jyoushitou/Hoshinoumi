# ===================== 记忆层路由（v32） =====================

from ..registry import PluginRegistry
from .bm25_retriever import BM25Retriever
from .sql_store import SQLMemoryStore

NATIVE = {
    "store": {"sql": SQLMemoryStore},
    "retriever": {"bm25": BM25Retriever},
}


class MemoryRouter:
    def __init__(self, registry=None, plugin_factory=None, plugin_store=None):
        self.registry = registry or PluginRegistry()
        self._plugin_factory = plugin_factory
        self.plugin_store = plugin_store
        self._cache = {}

    def native(self, kind, name):
        cls = NATIVE.get(kind, {}).get(str(name))
        return cls() if cls else None

    def _pick(self, kind, name):
        cap = f"memory.{kind}.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(kind, name)
        key = (kind, rec.name)
        if key in self._cache:
            return self._cache[key]
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
            self._cache[key] = obj
        return obj

    def memory_store(self, name="sql"):
        return self._pick("store", name)

    def retriever(self, name="bm25"):
        return self._pick("retriever", name)

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if k[1] != name}
