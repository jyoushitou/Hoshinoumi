# ===================== 通用工具模块 =====================
# 网络下载、Base64编码、图片消息构建
# 注：AI 回复解析已迁至 botv/ai/parse.py（v5-R2）

import os, base64
from .core.http import create_http_session
from .log import log_api

# 默认请求头，模拟浏览器访问，避免403
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}

def download_url(url):
    """下载URL内容，返回二进制数据，失败返回None"""
    if not url:
        log_api(f"[下载] URL为空")
        return None
    s=create_http_session()  # 创建带连接池的会话
    try:
        log_api(f"[下载] 开始下载: {url[:80]}")
        r=s.get(url,timeout=(5,10),verify=False,headers=DEFAULT_HEADERS)  # 5秒连接超时，10秒读取超时，添加浏览器UA头避免403
        r.raise_for_status()  # 检查HTTP状态码
        log_api(f"[下载] 成功: {len(r.content)} bytes")
        return r.content
    except Exception as e:
        log_api(f"[下载] 失败: {e}")
        return None
    finally:
        s.close()  # 关闭会话

def encode_image_base64(d):
    """将二进制图片数据编码为NapCat的base64格式"""
    try:
        return "base64://" + base64.b64encode(d).decode()
    except:
        return ""

def make_image_msg(filepath):
    """统一将本地图片路径转为 NapCat 图片消息体
    返回 [{"type":"image","data":{"file":"绝对路径"}}] 或 None"""
    if not filepath or not os.path.exists(filepath):
        return None
    abs_path = os.path.abspath(filepath)  # 转为绝对路径
    return [{"type":"image","data":{"file":abs_path}}]
