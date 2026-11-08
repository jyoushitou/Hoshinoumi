# ===================== 图片存储 =====================
# 本地路径 / 入库 / 去重 / 按标签搜索
# 迁移自 image.py（v5-R6）

import os
import hashlib

from ..config import IMAGE_DIR, CLIP_IMAGE_TAGS
from ..infra.conn import get_cursor
from ..log import log_api, log_err
from ..clip import analyze_image_with_clip
from ..utils import resolve_image_path


def image_local_path(md5_hash, ext="jpg"):
    """根据MD5和扩展名生成图片本地绝对路径"""
    os.makedirs(IMAGE_DIR, exist_ok=True)  # 确保图片目录存在
    rel = os.path.join(IMAGE_DIR, f"{md5_hash}.{ext}")  # 相对路径
    return os.path.abspath(rel)  # 转为绝对路径


def save_image_to_db(md5_hash, img_data, tags, source_url="", uid=""):
    """将图片数据存入数据库images表"""
    ext = "gif" if img_data[:6] in (b"GIF89a", b"GIF87a") else "jpg"  # 检测是否为GIF
    fp = image_local_path(md5_hash, ext)  # 生成文件路径
    try:
        c = get_cursor()
        c.execute(
            "INSERT IGNORE INTO images(md5_hash, image_data, tags, source_url, file_path, ext, use_count) VALUES(%s,%s,%s,%s,%s,%s,0)",
            (md5_hash, img_data, tags, source_url, fp, ext)  # 插入图片记录，use_count初始为0
        )
        c.connection.commit()
    except Exception as e:
        log_err(f"图片入库失败: {e}")


def load_image_from_db(md5_hash):
    """从数据库加载图片二进制数据和扩展名"""
    try:
        c = get_cursor()
        c.execute("SELECT image_data, ext FROM images WHERE md5_hash=%s", (md5_hash,))
        r = c.fetchone()
        if r:
            return r["image_data"], r["ext"]
    except Exception:
        pass
    return None, None


def image_already_exists(md5_hash):
    """检查图片是否已存在，返回(是否存在, 标签, 文件路径)"""
    try:
        c = get_cursor()
        c.execute("SELECT id, tags, file_path, ext FROM images WHERE md5_hash=%s", (md5_hash,))
        r = c.fetchone()
        if r:
            real = resolve_image_path(r["file_path"])
            if real:  # 文件已存在磁盘上（相对路径已按项目根解析）
                return True, r["tags"], real
            img_data, ext = load_image_from_db(md5_hash)  # 从数据库加载二进制数据
            if img_data:
                fp = image_local_path(md5_hash, ext)
                with open(fp, "wb") as f:
                    f.write(img_data)
                return True, r["tags"], fp
        return False, "", ""
    except Exception:
        return False, "", ""


async def process_and_save_image(img_data, source_url="", uid=""):
    """统一处理一张图片：CLIP打标→存本地→入库，返回(md5, tags_str, file_path)"""
    if not img_data:
        return None, "", ""
    md5 = hashlib.md5(img_data).hexdigest()  # 计算MD5哈希
    exists, tags_str, fp = image_already_exists(md5)
    if exists:  # 命中缓存
        log_api(f"图片命中缓存: {md5[:12]} tags={tags_str}")
        return md5, tags_str, fp
    tags, desc = await analyze_image_with_clip(img_data, CLIP_IMAGE_TAGS)  # CLIP分析图片
    tags_str = ",".join(tags)  # 标签列表转逗号分隔字符串
    ext = "gif" if img_data[:6] in (b"GIF89a", b"GIF87a") else "jpg"
    fp = image_local_path(md5, ext)
    with open(fp, "wb") as f:
        f.write(img_data)
    save_image_to_db(md5, img_data, tags_str, source_url, uid)
    log_api(f"图片已保存: {md5[:12]}.{ext} tags={tags_str}")
    return md5, tags_str, fp


def search_local_image_by_tags(keywords, limit=5):
    """从数据库按tags关键词搜索图片，返回[(md5, tags, file_path), ...]"""
    if not keywords:
        return []
    try:
        c = get_cursor()
        conds = " OR ".join(["tags LIKE %s" for _ in keywords[:3]])  # 构建LIKE条件（最多3个关键词）
        params = [f"%{kw}%" for kw in keywords[:3]]
        sql = f"SELECT md5_hash, tags, file_path, use_count FROM images WHERE {conds} ORDER BY use_count DESC LIMIT %s"
        params.append(limit)
        c.execute(sql, params)
        results = []
        for r in c.fetchall():
            real = resolve_image_path(r["file_path"])
            if real:
                results.append((r["md5_hash"], r["tags"], real))
        return results
    except Exception as e:
        log_err(f"搜索图片失败: {e}")
        return []


def get_random_local_image():
    """从数据库随机获取一张本地图片"""
    try:
        c = get_cursor()
        c.execute("SELECT md5_hash, tags, file_path FROM images ORDER BY RAND() LIMIT 1")
        r = c.fetchone()
        real = resolve_image_path(r["file_path"]) if r else None
        if real:
            return (r["md5_hash"], r["tags"], real)
    except Exception:
        pass
    return None


def materialize_image(fp):
    """把图片路径变成真实存在的绝对路径（v5-F4）

    - 相对路径按项目根解析
    - 文件丢了就按文件名里的 md5 从数据库 blob 恢复
    - 实在找不回来返回 None（调用方跳过发图，不要发坏路径）
    """
    p = resolve_image_path(fp)
    if p:
        return p
    md5 = os.path.splitext(os.path.basename(fp or ""))[0]
    if len(md5) == 32:
        exists, _tags, restored = image_already_exists(md5)
        if exists and restored:
            log_err(f"图片文件缺失，已从数据库恢复: {md5[:12]}")
            return restored
    log_err(f"图片路径无法解析: {fp}")
    return None
