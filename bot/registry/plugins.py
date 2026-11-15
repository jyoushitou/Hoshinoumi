# ===================== 插件注册表骨架（v27.1） =====================
# 只做内存注册/查找/列出；manifest 校验、版本/冲突在 v27.2。

from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import PluginConflictError
from .manifest import PluginManifest


@dataclass(frozen=True)
class PluginRecord:
    name: str
    capabilities: tuple
    factory: Callable
    priority: int = 0
    metadata: dict = field(default_factory=dict)
    manifest: object = None


class PluginRegistry:
    """第三方插件的内存注册表；核心 native 不注册进来。"""

    def __init__(self):
        self._by_name = {}
        self._by_cap = {}

    def register(self, name, capabilities, factory, priority=0, metadata=None, manifest=None):
        name = str(name or "").strip()
        if not name:
            raise ValueError("plugin name is required")
        if name in self._by_name:
            raise ValueError(f"plugin name duplicated: {name}")
        caps = tuple(str(c).strip() for c in capabilities if str(c).strip())
        if not caps:
            raise ValueError(f"plugin {name} has no capabilities")
        if not callable(factory):
            raise TypeError(f"plugin {name} factory is not callable")
        for cap in caps:
            for old in self._by_cap.get(cap, ()):
                if old.priority == int(priority):
                    raise PluginConflictError(
                        f"capability 冲突: {cap} 已被 {old.name} 以 priority={priority} 占用")
        rec = PluginRecord(name, caps, factory, int(priority), dict(metadata or {}), manifest)
        self._by_name[name] = rec
        for cap in caps:
            self._by_cap.setdefault(cap, []).append(rec)
        return rec

    def register_manifest(self, manifest: PluginManifest, factory):
        """校验 manifest 后注册；核心 native 不走这里。"""
        if not isinstance(manifest, PluginManifest):
            raise TypeError("manifest 必须是 PluginManifest")
        manifest.validate()
        return self._insert_manifest(manifest, factory)

    def _insert_manifest(self, manifest, factory):
        name = str(manifest.name or "").strip()
        if name in self._by_name:
            raise PluginConflictError(f"plugin name duplicated: {name}")
        if not callable(factory):
            raise TypeError(f"plugin {name} factory is not callable")
        caps = tuple(str(c) for c in manifest.capabilities)
        for cap in caps:
            for old in self._by_cap.get(cap, ()):
                if old.priority == int(manifest.priority):
                    raise PluginConflictError(
                        f"capability 冲突: {cap} 已被 {old.name} 以 priority={manifest.priority} 占用")
        rec = PluginRecord(name, caps, factory, int(manifest.priority),
                           manifest.to_dict(), manifest)
        self._by_name[name] = rec
        for cap in caps:
            self._by_cap.setdefault(cap, []).append(rec)
        return rec

    def get(self, capability, name=None):
        """按 capability 取实现；name 为空时返回优先级最高的一个。"""
        cap = str(capability or "").strip()
        rows = self._by_cap.get(cap, ())
        if name is not None:
            for r in rows:
                if r.name == str(name):
                    return r
            return None
        if not rows:
            return None
        return max(rows, key=lambda r: r.priority)

    def list(self):
        return sorted(self._by_name.values(), key=lambda r: (r.name,))

    def by_name(self, name):
        return self._by_name.get(str(name or ""))

    def snapshot(self):
        return [
            {"name": r.name, "capabilities": list(r.capabilities),
             "priority": r.priority, "metadata": dict(r.metadata)}
            for r in self.list()
        ]

    def clear(self):
        """测试用。"""
        self._by_name.clear()
        self._by_cap.clear()


def empty_registry():
    return PluginRegistry()
