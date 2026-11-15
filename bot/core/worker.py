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


def socket_path(name):
    d = Path(directory())
    d.mkdir(parents=True, exist_ok=True)
    return str(d / name)


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
    s.listen(backlog)
    return p, s
