# ===================== 在线图源 =====================
# ALAPI 斗图 / ACG 接口：拉取 → 下载 → 存库
# 迁移自 image.py（v5-R6）

import random

from botv.core import state as cfg
from ..log import log_api
from ..utils import download_url, DEFAULT_HEADERS
from ..core.http import create_http_session
from .store import process_and_save_image


async def fetch_and_save_acg_image():
    """从 ALAPI ACG 接口获取二次元图→下载→打标→入库，返回文件路径"""
    session = create_http_session()
    try:
        r = session.get("https://v3.alapi.cn/api/acg",  # 调用ALAPI ACG接口
                        params={"token": cfg.STICKER_API_ALAPI_TOKEN, "format": "json"},
                        timeout=10, verify=False, headers=DEFAULT_HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 200 and data.get("data"):
                img_url = data["data"].get("url") if isinstance(data["data"], dict) else None
                if img_url:
                    img_data = download_url(img_url)
                    if img_data:
                        md5, tags_str, fp = await process_and_save_image(img_data, img_url, "acg")
                        if fp:
                            return fp
    except Exception as e:
        log_api(f"ACG接口异常: {e}")
    finally:
        session.close()
    return None


async def search_alapi_and_save(keywords):
    """从 ALAPI 斗图接口搜图→下载→打标→入库，返回文件路径"""
    kw = "表情包 " + " ".join(keywords[:3])
    session = create_http_session()
    try:
        r = session.get("https://v3.alapi.cn/api/doutu",  # 调用ALAPI斗图接口
                        params={"token": cfg.STICKER_API_ALAPI_TOKEN, "keyword": kw},
                        timeout=10, verify=False, headers=DEFAULT_HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get("data") and isinstance(data["data"], list) and data["data"]:
                selected = random.choice(data["data"])
                img_url = selected if isinstance(selected, str) else selected.get("url") or selected.get("img")
                if img_url:
                    img_data = download_url(img_url)
                    if img_data:
                        md5, tags_str, fp = await process_and_save_image(img_data, img_url, "alapi")
                        if fp:
                            return fp
    except Exception as e:
        log_api(f"ALAPI搜图异常: {e}")
    finally:
        session.close()
    return None
