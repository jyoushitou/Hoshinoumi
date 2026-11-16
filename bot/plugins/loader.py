# ===================== 插件安装与加载（v28.4） =====================

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from ..registry.manifest import PluginManifest
from .context import make_context
from .errors import PluginLoadError, PluginError
from .store import PluginStore

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS = ROOT / "plugins"
LAYERS = {"models", "channels", "memory", "tools", "storage"}


def package_hash(path):
    h = hashlib.sha256()
    path = Path(path)
    for f in sorted(path.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts or f.suffix == ".pyc":
            continue
        h.update(f.relative_to(path).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def read_manifest(package):
    p = Path(package) / "plugin.json"
    if not p.exists():
        raise PluginLoadError("插件缺少 plugin.json")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise PluginLoadError(f"plugin.json 不是合法 JSON：{e}") from e
    manifest = PluginManifest.from_dict(data)
    manifest.validate()
    if manifest.layer not in LAYERS:
        raise PluginLoadError(f"非法 layer：{manifest.layer}")
    return manifest


def install_package(package, store=None, plugins_dir=None):
    package = Path(package)
    if not package.is_dir():
        raise PluginLoadError("只支持目录形式的插件包")
    manifest = read_manifest(package)
    digest = package_hash(package)
    store = store or PluginStore()
    old = store.get(manifest.name)
    if old is not None:
        if old.package_hash == digest:
            return old
        raise PluginLoadError(
            f"插件 {manifest.name} 已安装且 hash 不同；先卸载或改版本")
    root = Path(plugins_dir or PLUGINS) / manifest.layer / manifest.name
    if root.exists():
        raise PluginLoadError(f"目标目录已存在：{root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    tmp = root.with_name(root.name + ".installing")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(package, tmp)
    tmp.rename(root)
    try:
        store.insert(manifest, digest, path=str(root), enabled=False)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    return store.get(manifest.name)


def load_plugin(name, registry, store=None, plugins_dir=None):
    store = store or PluginStore()
    rec = store.get(name)
    if rec is None:
        raise PluginLoadError(f"插件未安装：{name}")
    if not rec.enabled:
        raise PluginLoadError(f"插件未启用：{name}")
    root = Path(rec.path or (Path(plugins_dir or PLUGINS) / rec.layer / rec.name))
    manifest = read_manifest(root)
    entry = manifest.entrypoint.split(":", 1)
    if len(entry) != 2:
        raise PluginLoadError("entrypoint 需要 module:factory")
    module_name, factory_name = entry
    py = root / (module_name.replace(".", "/") + ".py")
    if not py.exists():
        raise PluginLoadError(f"入口文件不存在：{py}")
    mod_name = f"nao_plugin_{manifest.name.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, py)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
        factory = getattr(mod, factory_name)
        ctx = make_context(manifest, registry=registry)
        registry.register_manifest(manifest, factory)
        try:
            obj = factory(ctx)
        except Exception:
            registry.unregister(manifest.name)
            raise
        return ctx, obj
    except Exception as e:
        store.record_error(name, type(e).__name__, str(e))
        raise PluginLoadError(f"加载失败：{e}") from e
