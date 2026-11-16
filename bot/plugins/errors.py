# ===================== 插件错误 =====================

class PluginError(Exception):
    """插件运行时错误。"""


class PluginLoadError(PluginError):
    """manifest/loader 拒绝加载。"""


class PluginTaskError(PluginError):
    """任务归属/取消失败。"""


class PermissionDenied(PluginError):
    """明确拒绝（level 0 / scope 不匹配 / 路径越界）。"""


class PermissionRequired(PluginError):
    """需要审批（level 1），v28.5 接审批流程。"""
