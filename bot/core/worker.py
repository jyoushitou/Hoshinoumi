# ===================== ingress / worker 模式（v25.2） =====================
# worker 不绑定 3001/27004，只监听 Unix socket；
# nao-ingress 持有对外端口，把 HTTP/WS 转发给 worker。

import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = str(ROOT / "data" / "worker")


def directory():
    return os.getenv("NAO_WORKER_SOCKET_DIR", DEFAULT_DIR)


def enabled():
    return os.getenv("NAO_WORKER_MODE", "0").strip().lower() in ("1", "true", "yes", "on")


def set_directory(path):
    os.environ["NAO_WORKER_SOCKET_DIR"] = str(path)
    os.environ["NAO_WORKER_MODE"] = "1"


def active_socket(name):
    """当前蓝绿版本的 socket；没有 current 就退回基础目录。"""
    base = Path(directory())
    cur = base / "current"
    try:
        if cur.exists() or cur.is_symlink():
            target = Path(os.readlink(cur)) if cur.is_symlink() else Path(cur.read_text().strip())
            if not target.is_absolute():
                target = base / target
            if target.exists():
                return str(target / name)
    except OSError:
        pass
    return socket_path(name)


def socket_path(name):
    d = Path(directory())
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return str(d / name)


def internal_api_socket():
    d = Path(directory())
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return str(d / "internal-api.sock")


def chmod_socket(path):
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def prepare_socket(name):
    """删除旧 socket 后返回路径；worker 启动时调用。"""
    p = socket_path(name)
    try:
        if os.path.exists(p):
            os.unlink(p)
    except OSError:
        pass
    return p


def bind_unix(name, backlog=128):
    p = prepare_socket(name)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(p)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    s.listen(backlog)
    return p, s
