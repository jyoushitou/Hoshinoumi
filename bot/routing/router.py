# ===================== 默认链路路由（v33.6.2） =====================

from ..plugins.permissions import PermissionDenied, PermissionRequired
from ..ports.route import Candidate, RouteKey
from .native import NativeRouteRegistry


class RouteRouter:
    def __init__(self, registry=None, plugin_store=None):
        self.registry = registry or __import__("bot.registry", fromlist=["PluginRegistry"]).PluginRegistry()
        self.plugin_store = plugin_store
        self._native = NativeRouteRegistry()

    def native(self, key):
        return self._native.resolve(key)

    def candidates(self, key):
        out = []
        for rec in self.registry.list():
            if not any(str(c).startswith(f"route.{key.layer}.") for c in rec.capabilities):
                continue
            if self.plugin_store is not None:
                try:
                    db = self.plugin_store.get(rec.name)
                    if db is not None and not db.enabled:
                        continue
                except Exception:
                    pass
            out.append(Candidate("plugin", rec.name, rec.priority, "unknown"))
        out.sort(key=lambda c: c.priority, reverse=True)
        out.append(Candidate("native", self._native.resolve(key).name, -1, "ok"))
        return out

    def resolve(self, key):
        """默认永远 native；插件只作为候选。"""
        return self.native(key)

    def explain(self, key):
        rows = self.candidates(key)
        lines = [f"🧭 {key.layer} 路由"]
        for c in rows:
            mark = "✅" if c.origin == "native" else "·"
            lines.append(f"  {mark} {c.origin}:{c.name} priority={c.priority} health={c.health}")
        lines.append("默认固定 native；插件只作为候选。")
        return "\n".join(lines)
