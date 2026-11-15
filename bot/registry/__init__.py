# ===================== 注册表包（v27） =====================
# 5 个注册表由 master 静态管理；插件注册表最后初始化。

from .plugins import PluginRecord, PluginRegistry
from .master import MasterRegistry, get_master, reset_master

__all__ = ["PluginRecord", "PluginRegistry", "MasterRegistry", "get_master", "reset_master"]
