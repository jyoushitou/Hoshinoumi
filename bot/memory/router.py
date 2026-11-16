# ===================== 记忆层路由（v32） =====================

from ..registry import PluginRegistry
from ..plugins.permissions import PermissionDenied, PermissionRequired
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

    def _native_default(self, kind):
        return self.native(kind, "sql" if kind == "store" else "bm25")

    def _pick(self, kind, name):
        cap = f"memory.{kind}.{name}@1"
        rec = self.registry.get(cap)
        if rec is None:
            return self.native(kind, name)
        if self.plugin_store is not None:
            try:
                db_rec = self.plugin_store.get(rec.name)
                if db_rec is not None and not db_rec.enabled:
                    return self._native_default(kind)
            except Exception:
                pass
        key = (kind, rec.name)
        if key in self._cache:
            return self._cache[key]
        try:
            if self._plugin_factory is not None:
                obj = self._plugin_factory(rec)
            else:
                from ..plugins.context import make_context
                ctx = make_context(rec.manifest, registry=self.registry)
                ctx.permissions.require("plugin.call", cap)
                obj = rec.factory(ctx)
        except (PermissionDenied, PermissionRequired):
            return self._native_default(kind)
        except Exception as e:
            self._record_error(rec.name, e)
            return self._native_default(kind)
        if obj is not None:
            self._cache[key] = obj
        return obj

    def memory_store(self, name="sql"):
        return self._pick("store", name)

    def retriever(self, name="bm25"):
        return self._pick("retriever", name)

    def _record_error(self, name, exc):
        if self.plugin_store is None:
            return
        try:
            self.plugin_store.record_error(name, type(exc).__name__, str(exc))
        except Exception:
            pass

    async def _call(self, kind, name, method, *args):
        p = self.memory_store(name) if kind == "store" else self.retriever(name)
        if p is None:
            return None
        try:
            return await getattr(p, method)(*args)
        except Exception as e:
            rec = self.registry.get(f"memory.{kind}.{name}@1")
            if rec is not None:
                self._record_error(rec.name, e)
                self.invalidate(rec.name)
            native = self.native(kind, "sql" if kind == "store" else "bm25")
            if native is not None:
                return await getattr(native, method)(*args)
            return None

    async def add(self, user_id, item, name="sql"):
        return await self._call("store", name, "add", user_id, item)

    async def delete(self, user_id, item_id, name="sql"):
        return await self._call("store", name, "delete", user_id, item_id)

    async def recent(self, user_id, n, name="sql"):
        return await self._call("store", name, "recent", user_id, n)

    async def search(self, user_id, query, top_k=5, name="bm25"):
        return await self._call("retriever", name, "search", user_id, query, top_k)

    def invalidate(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if k[1] != name}
