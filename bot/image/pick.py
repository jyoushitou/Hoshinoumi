# ===================== 选图 =====================
# 本地匹配 → ALAPI 在线搜 → 随机本地兜底
# 迁移自 image.py（v5-R6）

import random

from ..infra.conn import get_cursor
from .store import search_local_image_by_tags, get_random_local_image
from .fetch import search_alapi_and_save


async def get_best_image(keywords, uid=""):
    """核心发图函数：优先本地匹配→没有则ALAPI搜→搜到入库，返回文件路径"""
    results = search_local_image_by_tags(keywords, limit=5)  # 本地搜索（最多5张）
    if results:  # 本地有匹配
        selected = random.choice(results)  # 随机选一张
        try:
            c = get_cursor()
            c.execute("UPDATE images SET use_count=use_count+1 WHERE md5_hash=%s", (selected[0],))
            c.connection.commit()
        except Exception:
            pass  # 更新失败不影响
        return selected[2]
    fp = await search_alapi_and_save(keywords)  # 本地无匹配，ALAPI在线搜图
    if fp:
        return fp
    rand = get_random_local_image()  # ALAPI也没搜到，随机取一张本地图
    if rand:
        return rand[2]
    return None  # 完全无图可用
