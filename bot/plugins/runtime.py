# ===================== 插件进程生命周期（v28.6） =====================
# stop 跟随 worker：SIGTERM / drain / disable 都走这里。

import asyncio

from ..log import log_api, log_err, log_system
from ..registry import PluginRegistry
from .loader import load_plugin
from .store import PluginStore

_runtime = None


class PluginRuntime:
    def __init__(self, registry=None, store=None):
        self.registry = registry or PluginRegistry()
        self.store = store or PluginStore()
        self.loaded = {}

    def load_enabled(self):
        """启动时加载 enabled + auto_start 的插件；失败只记录，不拖垮 worker。"""
        n = 0
        for rec in self.store.list(enabled_only=True):
            if not rec.auto_start:
                continue
            try:
                ctx, obj = load_plugin(rec.name, self.registry, self.store)
                self.loaded[rec.name] = (ctx, obj)
                n += 1
                log_system(f"[插件] 已加载：{rec.name} {rec.version}")
            except Exception as e:
                log_err(f"[插件] 加载失败 {rec.name}: {e}")
        return n

    async def stop_one(self, name, timeout=5.0):
        item = self.loaded.pop(str(name), None)
        if not item:
            return False
        ctx, _obj = item
        try:
            await ctx.tasks.cancel_all(timeout=timeout)
        except Exception as e:
            log_err(f"[插件] 取消任务失败 {name}: {e}")
        try:
            await asyncio.wait_for(ctx.lifecycle.stop(), timeout=timeout)
        except asyncio.TimeoutError:
            log_err(f"[插件] stop 超时 {name}")
        except Exception as e:
            log_err(f"[插件] stop 失败 {name}: {e}")
        try:
            self.registry.unregister(name)
        except Exception:
            pass
        log_api(f"[插件] 已停止：{name}")
        return True

    async def stop_all(self, timeout=5.0):
        names = list(self.loaded)
        for name in names:
            await self.stop_one(name, timeout=timeout)
        return len(names)

    def disable(self, name, timeout=5.0):
        self.store.set_enabled(name, False)
        return asyncio.create_task(self.stop_one(name, timeout=timeout))


def get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = PluginRuntime()
    return _runtime


def reset_runtime():
    global _runtime
    _runtime = None
