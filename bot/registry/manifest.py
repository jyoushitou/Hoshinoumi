# ===================== PluginManifest（v27.2） =====================

import re
from dataclasses import dataclass, field

from .errors import CapabilityUnsupportedError, ManifestError

_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
_CAP_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+@([1-9][0-9]*)$")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$")
_LAYERS = {"models", "channels", "memory", "tools", "storage",
           "scheduler", "outbound", "routes"}
_SUPPORTED_API = {1}
_SUPPORTED_CAP = {1}


def parse_semver(text):
    """支持三段（旧版）和四段（v33+）版本号。"""
    m = _SEMVER_RE.match(str(text or "").strip().lstrip("v"))
    if not m:
        raise ManifestError(f"非法版本号: {text!r}，需要 x.y.z 或 x.y.z.w")
    return tuple(int(x) for x in m.groups() if x is not None)


def parse_capability(cap):
    m = _CAP_RE.match(str(cap or "").strip())
    if not m:
        raise ManifestError(f"非法 capability: {cap!r}，需要 domain.name@1")
    return int(m.group(2))


def check_requires_core(spec, core_version):
    """当前只支持 >=x.y.z；其他约束直接拒绝，避免假装兼容。"""
    spec = str(spec or "").strip()
    if not spec.startswith(">="):
        raise ManifestError(f"requires_core 只支持 >=x.y.z: {spec!r}")
    need = parse_semver(spec[2:].strip())
    have = parse_semver(core_version)
    if have < need:
        raise ManifestError(f"requires_core {spec} 不满足，当前 {core_version}")


@dataclass(frozen=True)
class PluginManifest:
    name: str
    author: str
    layer: str
    version: str
    api_version: int
    requires_core: str
    capabilities: tuple
    entrypoint: str
    auto_start: bool = False
    priority: int = 0
    metadata: dict = field(default_factory=dict)

    def validate(self):
        if not _NAME_RE.match(str(self.name or "")):
            raise ManifestError(f"非法插件名: {self.name!r}")
        if not str(self.author or "").strip():
            raise ManifestError("author 不能为空")
        if self.layer not in _LAYERS:
            raise ManifestError(f"非法 layer: {self.layer!r}")
        parse_semver(self.version)
        if int(self.api_version) not in _SUPPORTED_API:
            raise CapabilityUnsupportedError(
                f"不支持的 api_version={self.api_version}，核心只支持 {sorted(_SUPPORTED_API)}")
        check_requires_core(self.requires_core, _core_version())
        caps = tuple(self.capabilities)
        if not caps:
            raise ManifestError("capabilities 不能为空")
        if len(set(caps)) != len(caps):
            raise ManifestError("capabilities 有重复")
        for cap in caps:
            ver = parse_capability(cap)
            if ver not in _SUPPORTED_CAP:
                raise CapabilityUnsupportedError(
                    f"不支持的 capability 版本: {cap}；核心只支持 @1")
        ep = str(self.entrypoint or "")
        if ":" not in ep or not ep.split(":", 1)[0] or not ep.split(":", 1)[1]:
            raise ManifestError("entrypoint 需要 module:factory")
        return self

    def to_dict(self):
        return {
            "name": self.name, "author": self.author, "layer": self.layer,
            "version": self.version, "api_version": self.api_version,
            "requires_core": self.requires_core,
            "capabilities": list(self.capabilities),
            "entrypoint": self.entrypoint, "auto_start": bool(self.auto_start),
            "priority": int(self.priority), "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, data):
        try:
            return cls(
                name=data["name"], author=data["author"], layer=data["layer"],
                version=data["version"], api_version=int(data.get("api_version", 1)),
                requires_core=data.get("requires_core", ">=0.0.0"),
                capabilities=tuple(data.get("capabilities") or ()),
                entrypoint=data.get("entrypoint", "plugin:factory"),
                auto_start=bool(data.get("auto_start", False)),
                priority=int(data.get("priority", 0)),
                metadata=dict(data.get("metadata") or {}),
            )
        except KeyError as e:
            raise ManifestError(f"manifest 缺少字段: {e}") from e


def _core_version():
    from ..core.version import get_version
    return get_version()
