# ===================== 密钥仓储 =====================
# 迁移自 db.py（v5-R6）

import os

from bot.core import state as cfg
from ..log import log_system
from .conn import get_cursor


def get_api_key_from_db(name):
    """从数据库api_keys表获取指定密钥"""
    c = get_cursor()
    c.execute("SELECT key_value FROM api_keys WHERE key_name=%s", (name,))
    r = c.fetchone()
    return r["key_value"] if r else ""


def _key(name):
    """DB 优先；DB 没有时允许环境变量（部署时更方便）"""
    return get_api_key_from_db(name) or os.getenv(name, "")


def reload_api_keys():
    """重新加载所有API密钥到全局变量（DB > 环境变量）"""
    cfg.DS_API_KEY = _key("DS_API_KEY")  # DeepSeek密钥
    cfg.DOUBAO_API_KEY = _key("ARK_API_KEY")  # 豆包密钥
    cfg.STICKER_API_ALAPI_TOKEN = _key("ALAPI_TOKEN")  # ALAPI搜图密钥
    log_system(f"API: DS={bool(cfg.DS_API_KEY)},豆包={bool(cfg.DOUBAO_API_KEY)},ALAPI={bool(cfg.STICKER_API_ALAPI_TOKEN)}")

def save_api_key(name, value, cursor=None):
    """写入/覆盖一条 api_keys（v17.16：server 层不再写 SQL）

    MySQL 用 ON DUPLICATE KEY，SQLite 用 INSERT OR REPLACE。
    """
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from .conn import get_cursor

            c = get_cursor()
        backend = ""
        try:
            from .conn import _resolve_backend

            backend = _resolve_backend()
        except Exception:
            backend = ""
        if backend == "sqlite":
            c.execute("INSERT OR REPLACE INTO api_keys (key_name, key_value) "
                      "VALUES (%s, %s)", (name, value))
        else:
            c.execute("INSERT INTO api_keys (key_name, key_value) VALUES (%s, %s) "
                      "ON DUPLICATE KEY UPDATE key_value=%s", (name, value, value))
        c.connection.commit()
        return True
    except Exception:
        return False
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass
