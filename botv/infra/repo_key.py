# ===================== 密钥仓储 =====================
# 迁移自 db.py（v5-R6）

from botv.core import state as cfg
from ..log import log_system
from .conn import get_cursor


def get_api_key_from_db(name):
    """从数据库api_keys表获取指定密钥"""
    c = get_cursor()
    c.execute("SELECT key_value FROM api_keys WHERE key_name=%s", (name,))
    r = c.fetchone()
    return r["key_value"] if r else ""


def reload_api_keys():
    """重新加载所有API密钥到全局变量"""
    cfg.DS_API_KEY = get_api_key_from_db("DS_API_KEY")  # DeepSeek密钥
    cfg.DOUBAO_API_KEY = get_api_key_from_db("ARK_API_KEY")  # 豆包密钥
    cfg.STICKER_API_ALAPI_TOKEN = get_api_key_from_db("ALAPI_TOKEN")  # ALAPI搜图密钥
    log_system(f"API: DS={bool(cfg.DS_API_KEY)},豆包={bool(cfg.DOUBAO_API_KEY)},ALAPI={bool(cfg.STICKER_API_ALAPI_TOKEN)}")
