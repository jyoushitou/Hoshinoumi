# ===================== 注册表管理器（v27.1） =====================
# 静态登记 5 个注册表；插件注册表最后初始化。
# 这里只读快照，不接管各注册表的写入。

from dataclasses import dataclass
from typing import Callable

from .plugins import PluginRegistry


@dataclass(frozen=True)
class RegistryRef:
    name: str
    kind: str
    snapshot: Callable
    health: Callable


class MasterRegistry:
    """5 个注册表的只读管理器；不支持运行时新增注册表。"""

    NAMES = ("command", "events", "life", "ai", "plugin")

    def __init__(self, plugin_registry=None):
        self.plugin = plugin_registry or PluginRegistry()
        self._refs = {}
        # 固定顺序：命令 → 事件 → 生活 → AI → 插件（最后）
        self._refs["command"] = RegistryRef(
            "command", "core", self._command_snapshot, self._always_ok)
        self._refs["events"] = RegistryRef(
            "events", "core", self._events_snapshot, self._always_ok)
        self._refs["life"] = RegistryRef(
            "life", "core", self._life_snapshot, self._always_ok)
        self._refs["ai"] = RegistryRef(
            "ai", "core", self._ai_snapshot, self._always_ok)
        self._refs["plugin"] = RegistryRef(
            "plugin", "plugin", self._plugin_snapshot, self._plugin_health)

    @staticmethod
    def _always_ok():
        return True

    def _command_snapshot(self):
        from ..cmd import registry as cmd_reg
        return sorted(cmd_reg.COMMANDS)

    def _events_snapshot(self):
        from ..events import registry as ev_reg
        return ev_reg.snapshot()

    def _events_health(self):
        from ..events import registry as ev_reg
        return bool(ev_reg.kinds())

    def _life_snapshot(self):
        from ..core import lifeport
        return lifeport.available()

    def _ai_snapshot(self):
        from ..core import ai_port
        return ai_port.available()

    def _plugin_snapshot(self):
        return self.plugin.snapshot()

    def _plugin_health(self):
        return True

    def names(self):
        return list(self.NAMES)

    def get_ref(self, name):
        return self._refs.get(str(name or ""))

    def snapshot(self):
        out = {}
        for name in self.NAMES:
            ref = self._refs[name]
            items = ref.snapshot()
            out[name] = {"kind": ref.kind, "count": len(items), "items": items}
        return out

    def health(self):
        return {name: bool(self._refs[name].health()) for name in self.NAMES}


_master = None


def get_master():
    global _master
    if _master is None:
        _master = MasterRegistry()
    return _master


def reset_master():
    """测试用：重建管理器，不重建业务注册表。"""
    global _master
    _master = None
