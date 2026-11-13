# ===================== 在线图源 =====================
# ALAPI 斗图 / ACG 接口：拉取 → 下载 → 存库
# 迁移自 image.py（v5-R6）
# v8-FIX：所有同步 HTTP 都丢到线程里跑，避免卡住事件循环导致 keepalive 超时

import asyncio
import random

from ..infra.blocking import run_blocking  # v17.0.3：阻塞调用统一入口
from ..core import state as cfg  # 运行时变量（Token 从数据库加载）
from ..log import log_api
from ..utils import download_url, DEFAULT_HEADERS
from ..core.http import get_http_session
from .store import process_and_save_image


async def _get(session, url, **kwargs):
    """同步 session.get 丢进线程，别阻塞事件循环"""
    return await run_blocking(lambda: session.get(url, **kwargs),
                              timeout=30, name="image-get")  # v17.0.3：统一线程池


async def _download(url):
    """同步下载丢进线程"""
    return await run_blocking(download_url, url, timeout=60, name="image-download")  # v17.0.3


async def fetch_and_save_acg_image():
    """从 ALAPI ACG 接口获取二次元图→下载→打标→入库，返回文件路径"""
    session = get_http_session()
    try:
        r = await _get(session, "https://v3.alapi.cn/api/acg",
                       params={"token": cfg.STICKER_API_ALAPI_TOKEN, "format": "json"},
                       timeout=10, verify=False, headers=DEFAULT_HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 200 and data.get("data"):
                img_url = data["data"].get("url") if isinstance(data["data"], dict) else None
                if img_url:
                    img_data = await _download(img_url)
                    if img_data:
                        md5, tags_str, fp = await process_and_save_image(img_data, img_url, "acg", keywords=["二次元"])
                        if fp:
                            return fp
    except Exception as e:
        log_api(f"ACG接口异常: {e}")
    return None


async def search_alapi_and_save(keywords):
    """从 ALAPI 斗图接口搜图→下载→打标→入库，返回文件路径"""
    kw = "表情包 " + " ".join(keywords[:3])
    session = get_http_session()
    try:
        r = await _get(session, "https://v3.alapi.cn/api/doutu",
                       params={"token": cfg.STICKER_API_ALAPI_TOKEN, "keyword": kw},
                       timeout=10, verify=False, headers=DEFAULT_HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get("data") and isinstance(data["data"], list) and data["data"]:
                # v8-FIX：坏源（403 防盗链）直接换下一张，不在同一张上重试
                urls = []
                for item in data["data"]:
                    u = item if isinstance(item, str) else (item.get("url") or item.get("img"))
                    if u:
                        urls.append(u)
                random.shuffle(urls)
                for img_url in urls[:3]:
                    img_data = await _download(img_url)
                    if not img_data:
                        continue
                    md5, tags_str, fp = await process_and_save_image(img_data, img_url, "alapi", keywords=keywords)
                    if fp:
                        return fp
    except Exception as e:
        log_api(f"ALAPI搜图异常: {e}")
    return None
