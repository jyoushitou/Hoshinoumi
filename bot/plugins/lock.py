# ===================== plugin-lock（v28.4） =====================

import json
from pathlib import Path

from .errors import PluginLoadError


def write_lock(version_dir, generation, plugins):
    data = {
        "registry_generation": int(generation),
        "plugins": [
            {"name": p.name, "version": p.version, "hash": p.package_hash,
             "layer": p.layer, "capabilities": list(p.capabilities)}
            for p in plugins
        ],
    }
    path = Path(version_dir) / "plugin-lock.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def read_lock(version_dir):
    path = Path(version_dir) / "plugin-lock.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise PluginLoadError(f"plugin-lock.json 损坏：{e}") from e


def verify_generation(lock, generation):
    if lock is None:
        return True
    return int(lock.get("registry_generation", -1)) == int(generation)
