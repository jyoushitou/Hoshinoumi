# ===================== 注册表错误（v27.2） =====================

class RegistryError(ValueError):
    """注册表/插件契约错误。"""


class ManifestError(RegistryError):
    """manifest 字段非法。"""


class PluginConflictError(RegistryError):
    """插件名或 capability 冲突。"""


class CapabilityUnsupportedError(RegistryError):
    """核心不支持该 capability 版本（例如 @2）。"""
