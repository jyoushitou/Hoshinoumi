# ===================== 进程名（v35.4.15） =====================
# 统一把后端进程显示为 nao-run。
# Linux: prctl(PR_SET_NAME) 让 ps -o comm= / pgrep -x 命中；
#        装了 setproctitle 时同时改写 argv。
# Windows: 控制台标题设为 nao-run；任务管理器进程名需要 nao-run 启动器/包装器。
# 任何一步失败都不影响启动。

import ctypes
import os
import sys

PROCESS_NAME = "nao-run"


def _set_linux_comm(name: str) -> bool:
    try:
        libc = ctypes.CDLL(None)
        # PR_SET_NAME = 15；comm 最长 15 字节
        return libc.prctl(15, name.encode("utf-8")[:15], 0, 0, 0) == 0
    except Exception:
        return False


def _set_proctitle(name: str) -> bool:
    try:
        import setproctitle  # type: ignore

        setproctitle.setproctitle(name)
        return True
    except Exception:
        return False


def _set_windows_title(name: str) -> bool:
    try:
        return bool(ctypes.windll.kernel32.SetConsoleTitleW(name))
    except Exception:
        return False


def set_process_name(name: str | None = None) -> None:
    """设置当前进程名；失败静默，不影响后端启动。"""
    name = name or os.environ.get("NAO_PROCESS_NAME", PROCESS_NAME)
    _set_proctitle(name)
    if sys.platform.startswith("linux"):
        _set_linux_comm(name)
    elif os.name == "nt":
        _set_windows_title(name)


def current_process_name() -> str:
    """便于测试/诊断：Linux 读 /proc/self/comm，其他平台返回当前设置名。"""
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/comm", "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return PROCESS_NAME
