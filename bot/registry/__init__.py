# ===================== 注册表包（v27） =====================
# 5 个注册表由 master 静态管理；插件注册表最后初始化。

from .errors import (CapabilityUnsupportedError, ManifestError, PluginConflictError, RegistryError)
from .manifest import PluginManifest
from .plugins import PluginRecord, PluginRegistry
from .master import MasterRegistry, get_master, reset_master

__all__ = ["PluginRecord", "PluginRegistry", "PluginManifest", "RegistryError",
           "ManifestError", "PluginConflictError", "CapabilityUnsupportedError",
           "MasterRegistry", "get_master", "reset_master", "snapshot", "health"]


def snapshot():
    """5 个注册表的只读快照。"""
    return get_master().snapshot()


def health():
    """5 个注册表的健康状态。"""
    return get_master().health()
