# ===================== TXT 日志（v17.5） =====================
# 除了控制台和数据库，再写一份按天切的 txt 文件，保留 180 天（半年）。
#
#     logs/nao-2026-11-11.log
#     logs/nao-2026-11-12.log
#
# 设计：
#   - 按天一个文件，追加写（崩溃不丢已有内容）
#   - 单文件超 64MB 自动加序号（.1 .2）
#   - 启动 + 跨天时清理超期文件；数据库 logs 表同一节奏清理
#   - 写失败绝不影响主流程（吞异常）
#   - 线程安全：一把锁
#
# 配置：
#   NAO_LOG_DIR       日志目录，默认 logs
#   NAO_LOG_KEEP_DAYS 保留天数，默认 180
#   NAO_LOG_TXT       0 关闭

import os
import threading
from datetime import datetime, timedelta

MAX_SIZE = 64 * 1024 * 1024
_lock = threading.Lock()
_state = {"day": None, "path": None, "size": 0, "inited": False}


def _dir():
    return os.getenv("NAO_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def keep_days():
    try:
        return max(1, int(os.getenv("NAO_LOG_KEEP_DAYS", "180")))
    except Exception:
        return 180


def enabled():
    return os.getenv("NAO_LOG_TXT", "1") not in ("0", "false", "False", "")


def _path_for(day):
    return os.path.join(_dir(), f"nao-{day}.log")


def _rotate_if_needed(path):
    try:
        if os.path.exists(path) and os.path.getsize(path) >= MAX_SIZE:
            i = 1
            while os.path.exists(f"{path}.{i}"):
                i += 1
            return f"{path}.{i}"
    except Exception:
        pass
    return path


def write(tag, message):
    """写一行：时间|级别|内容；失败静默"""
    if not enabled():
        return False
    try:
        with _lock:
            day = datetime.now().strftime("%Y-%m-%d")
            if _state["day"] != day or not _state["path"]:
                os.makedirs(_dir(), exist_ok=True)
                _state["day"] = day
                _state["path"] = _path_for(day)
                if not _state["inited"]:
                    cleanup()
                    purge_db_logs()
                    _state["inited"] = True

            path = _rotate_if_needed(_state["path"])
            _state["path"] = path
            line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{tag}|{message}\n"
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
            _state["size"] = os.path.getsize(path)
        return True
    except Exception:
        return False


def cleanup():
    """删掉超过保留期的日志文件"""
    cutoff = datetime.now() - timedelta(days=keep_days())
    removed = 0
    try:
        d = _dir()
        if not os.path.isdir(d):
            return 0
        for name in os.listdir(d):
            if not (name.startswith("nao-") and ".log" in name):
                continue
            try:
                day = datetime.strptime(name.split("nao-", 1)[1][:10], "%Y-%m-%d")
            except Exception:
                continue
            if day < cutoff:
                try:
                    os.remove(os.path.join(d, name))
                    removed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return removed


def purge_db_logs(days=None):
    """数据库 logs 表也按同一保留期清理（分批，避免长事务）"""
    days = keep_days() if days is None else days
    total = 0
    try:
        from ..infra.conn import get_cursor
        c = get_cursor()
        for _ in range(20):
            c.execute(
                "DELETE FROM logs WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY) "
                "LIMIT 1000", (int(days),))
            n = getattr(c, "rowcount", 0) or 0
            total += n
            if n < 1000:
                break
        c.connection.commit()
    except Exception:
        return 0
    return total


def stats():
    d = _dir()
    files, total = 0, 0
    try:
        if os.path.isdir(d):
            for name in os.listdir(d):
                if name.startswith("nao-") and ".log" in name:
                    files += 1
                    total += os.path.getsize(os.path.join(d, name))
    except Exception:
        pass
    return {"enabled": enabled(), "dir": d, "keep_days": keep_days(),
            "files": files, "size_mb": round(total / 1024 / 1024, 2)}


def describe():
    s = stats()
    if not s["enabled"]:
        return "📝 文件日志：已关闭"
    return (f"📝 文件日志：{s['files']} 个文件 / {s['size_mb']} MB"
            f"（保留 {s['keep_days']} 天）")
