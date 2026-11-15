# ===================== 热加载：配置/提示词/人设（v25.1） =====================
# 不重启进程，文件变化后下一轮生效。
# 只热加载“读文件”的配置和文本；业务代码热更新在 v25.3/v25.4 的蓝绿 worker。

import asyncio
import os
from pathlib import Path

from ..log import log_api, log_system
from . import appconfig

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config.local.json"
PERSONA_ROOT = ROOT / "personas"
SUPPLEMENT = ROOT / "bot" / "personality_supplement.txt"
INTERVAL = float(os.getenv("NAO_HOT_RELOAD_INTERVAL", "3"))
ENABLED = os.getenv("NAO_HOT_RELOAD", "1").strip().lower() not in ("0", "false", "no", "off")

_snapshot = {}


def _paths():
    out = [CONFIG_FILE, SUPPLEMENT]
    if PERSONA_ROOT.exists():
        for p in PERSONA_ROOT.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".txt", ".active", ".json"):
                out.append(p)
    return out


def scan():
    """返回 {path: (mtime_ns, size)}；用于测试和 watcher。"""
    snap = {}
    for p in _paths():
        try:
            st = p.stat()
            snap[str(p)] = (st.st_mtime_ns, st.st_size)
        except OSError:
            continue
    return snap


def changed(before, after):
    return any(after.get(k) != v for k, v in before.items()) or any(
        k not in before for k in after)


def reload_now():
    """配置和提示词一起重载；失败只记录，不影响主循环。"""
    try:
        appconfig.reload()
    except Exception as e:
        log_api(f"[热加载] 配置重载失败: {e}")
    try:
        from ..ai.prompt import reload_personality_supplement
        reload_personality_supplement()
    except Exception as e:
        log_api(f"[热加载] 人设重载失败: {e}")
    log_system("[热加载] 配置/提示词已重新读取")


async def watch(stop_event=None):
    """后台轮询；文件变化时热加载。"""
    global _snapshot
    if not ENABLED:
        log_system("[热加载] 已关闭（NAO_HOT_RELOAD=0）")
        return
    _snapshot = scan()
    log_system(f"[热加载] 监控 {len(_snapshot)} 个文件，间隔 {INTERVAL:.0f}s")
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        await asyncio.sleep(INTERVAL)
        now = scan()
        if changed(_snapshot, now):
            _snapshot = now
            reload_now()
