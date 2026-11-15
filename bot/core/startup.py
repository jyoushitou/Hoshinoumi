# ===================== 启动模式判定（v25.7） =====================
# first：第一次真正启动
# hot  ：supervisor 从旧版本热更过来（NAO_WORKER_VERSION 存在且版本变了）
# normal：普通重启/同版本重连

import os

from .version import get_version


def detect():
    from ..infra import repo_meta

    current = get_version()
    first = repo_meta.get_value("first_start")
    prev = repo_meta.get_value("version") or ""
    worker_version = (os.getenv("NAO_WORKER_VERSION") or "").strip()

    if not first:
        mode = "first"
    elif worker_version and prev and prev.lstrip("v") != current.lstrip("v"):
        mode = "hot"
    else:
        mode = "normal"
    return mode, prev, current
