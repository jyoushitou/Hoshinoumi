# ===================== 单实例锁（v7-E32） =====================
# 用文件锁保证「同一时刻只跑一个 bot」。
# 进程退出时操作系统自动释放，不会留下「僵尸锁」。
#
# 锁文件和 PID 文件是分开的：
#   .botv.lock      —— 只用来加锁，内容不读（Windows 字节锁会挡住读）
#   .botv.lock.pid  —— 纯文本，写当前 PID，只为在「已有实例」时给人看

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCK_FILE = os.path.join(_ROOT, ".botv.lock")
PID_FILE = os.path.join(_ROOT, ".botv.lock.pid")

_handle = None  # 持有文件句柄，进程活着锁就在


def _try_lock(fh):
    """跨平台的「非阻塞独占锁」"""
    try:
        import fcntl  # Unix：flock 是建议锁
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except ImportError:
        pass
    except OSError:
        return False

    try:
        import msvcrt  # Windows：字节锁（强制锁，所以单独用个文件）
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def acquire(path=None):
    """拿到锁返回 True；已有实例在跑返回 False"""
    global _handle
    lock_path = path or LOCK_FILE
    pid_path = (path + ".pid") if path else PID_FILE

    fh = open(lock_path, "a+")
    if not _try_lock(fh):
        fh.close()
        return False

    _handle = fh  # 保持引用，别让 GC 关掉
    try:
        with open(pid_path, "w", encoding="utf-8") as pf:
            pf.write(str(os.getpid()))
    except Exception:
        pass  # PID 文件只是提示用，写不进去不影响锁
    return True


def release(path=None):
    """主动释放（正常退出时调用；异常退出靠系统回收）"""
    global _handle
    if _handle:
        try:
            _handle.close()
        except Exception:
            pass
        _handle = None


def holder_pid(path=None):
    """读 PID 文件里记录的进程号（仅用于提示）"""
    pid_path = (path + ".pid") if path else PID_FILE
    try:
        with open(pid_path, "r", encoding="utf-8") as f:
            return f.read(32).strip()
    except Exception:
        return ""
