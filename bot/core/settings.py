# ===================== 配置加载（v16） =====================
# 敏感配置不再写死在代码里。优先级：
#
#   1. 环境变量（NAO_*）
#   2. 本地配置文件 config.local.json（已在 .gitignore，不会进版本库）
#   3. 空默认值 / 安全占位符
#
# 也就是说：**代码里只有空壳**，真实值从文件或环境变量来。
#
# config.local.json 示例见 config.example.json。

import copy
import json
import logging
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(ROOT, "config.local.json")

DEFAULTS = {
    "master_qq": "",
    "ws_port": 3001,
    "api_port": 27004,
    "db": {
        "backend": "auto",         # auto：能用 MySQL 就用，连不上退 SQLite
        "path": "data/nao.db",     # sqlite 文件位置
        "host": "",
        "port": 3306,
        "user": "",
        "password": "",
        "name": "",
    },
}

# 环境变量 → 配置路径
ENV_MAP = {
    "NAO_MASTER_QQ": "master_qq",
    "NAO_WS_PORT": "ws_port",
    "NAO_API_PORT": "api_port",
    "NAO_DB_BACKEND": "db.backend",
    "NAO_DB_PATH": "db.path",
    "NAO_DB_HOST": "db.host",
    "NAO_DB_PORT": "db.port",
    "NAO_DB_USER": "db.user",
    "NAO_DB_PASS": "db.password",
    "NAO_DB_NAME": "db.name",
}

_cache = None


def _set_path(data, path, value):
    keys = path.split(".")
    cur = data
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _get_path(data, path, default=None):
    cur = data
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _coerce(key, value):
    """端口类转 int，其余保字符串"""
    if key.endswith(("port", "_qq")):
        try:
            return int(str(value).strip())
        except Exception:
            return value
    return value


def load(force=False):
    """读配置：文件 → 环境变量覆盖"""
    global _cache
    if _cache is not None and not force:
        return _cache

    data = copy.deepcopy(DEFAULTS)

    # 1. 本地配置文件
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                file_cfg = json.load(f) or {}
            for k, v in file_cfg.items():
                if isinstance(v, dict) and isinstance(data.get(k), dict):
                    data[k].update(v)
                else:
                    data[k] = v
        except Exception:
            pass

    # 2. 环境变量覆盖（最高优先级）
    for env_name, path in ENV_MAP.items():
        raw = os.getenv(env_name)
        if raw is not None and str(raw).strip() != "":
            _set_path(data, path, _coerce(path, raw))

    _cache = data
    return data


def get(path, default=None):
    """取配置项，支持点号路径：get("db.host")"""
    return _get_path(load(), path, default)


_backend_cache = {"value": None}


def mysql_reachable(timeout=3.0):
    """MySQL 能不能连（连不上就返回 False，不抛异常）"""
    try:
        import pymysql

        db = load().get("db", {})
        if not db.get("host"):
            return False
        conn = pymysql.connect(
            host=db.get("host"), port=int(db.get("port") or 3306),
            user=db.get("user") or "", password=db.get("password") or "",
            database=db.get("name") or "", charset="utf8mb4",
            connect_timeout=int(timeout))
        conn.close()
        return True
    except Exception as e:
        # v21.5：settings 不再反向 import log；用标准库日志打断持久层环
        logging.getLogger("settings").warning(
            "[存储] MySQL 不可用（%s），改用 SQLite", type(e).__name__)
        return False


def storage_backend(force="", timeout=3.0):
    """用哪个存储后端

    - 配了 `mysql` / `sqlite`：照配的来（强制）
    - `auto`（默认）：**先试 MySQL，连不上才退 SQLite**
    """
    if force:
        _backend_cache["value"] = None
    backend = str(load().get("db", {}).get("backend") or "auto").strip().lower()

    if backend in ("sqlite", "sqlite3", "file"):
        return "sqlite"
    if backend in ("mysql", "mariadb"):
        return "mysql"

    # auto
    if _backend_cache["value"] is None:
        _backend_cache["value"] = "mysql" if mysql_reachable(timeout) else "sqlite"
    return _backend_cache["value"]


def sqlite_path():
    """sqlite 数据文件路径（相对项目根目录）"""
    raw = str(load().get("db", {}).get("path") or "data/nao.db")
    return raw if os.path.isabs(raw) else os.path.join(ROOT, raw)


def db_config():
    """给 pymysql 用的连接参数"""
    db = load().get("db", {})
    return {
        "host": db.get("host") or "",
        "port": int(db.get("port") or 3306),
        "user": db.get("user") or "",
        "password": db.get("password") or "",
        "database": db.get("name") or "",
        "charset": "utf8mb4",
    }


def missing_keys():
    """哪些必填项还没配（空 → 启动时提示）"""
    db = load().get("db", {})
    missing = []
    if not db.get("host"):
        missing.append("NAO_DB_HOST（或 config.local.json 的 db.host）")
    if not db.get("user"):
        missing.append("NAO_DB_USER（或 db.user）")
    if not db.get("password"):
        missing.append("NAO_DB_PASS（或 db.password）")
    if not db.get("name"):
        missing.append("NAO_DB_NAME（或 db.name）")
    return missing


def describe_source():
    """日志用：配置从哪来的"""
    parts = []
    if os.path.exists(CONFIG_FILE):
        parts.append("config.local.json")
    if any(os.getenv(k) for k in ENV_MAP):
        parts.append("环境变量")
    return " + ".join(parts) if parts else "默认值（未配置）"


